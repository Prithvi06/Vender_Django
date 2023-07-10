import hashlib
import json
import logging
from datetime import date
from typing import Optional

from celery import shared_task
from django.db.models import Max, Q
from django.utils import timezone

from apps.administrator.models import (
    OFACSDNResult,
    OFACSpeciallyDesignatedNational,
    OFACSpeciallyDesignatedNationalAddress,
    OFACSpeciallyDesignatedNationalAlternate,
    ScheduledJobLogger,
)
from apps.authentication.models import User
from apps.tasks.models import Task, TaskPriority, TaskStatus
from apps.utility.EmailServices import email_service
from apps.utility.VendorUtilities import get_contract_activity, get_search_ratio
from .models import Contact, Contract, Vendor, SurveyToken, ContractStatus

SDN_TASK_TITLE = "Possible OFAC Hit - %s"
SDN_TASK_DESCRIPTION = "We found a match between %s and \
someone on the OFAC list.  Please click here \
https://sanctionssearch.ofac.treas.gov/ to research this person \
further."


def get_description(contract):
    if contract.is_auto_renew:
        return f""" {contract.title} ends on
                    {contract.next_expiration}. If you wish to extend
                    the contract, please do so befor that date."""

    else:
        return f"""{contract.title} is set to auto renew on
                   {contract.next_expiration}. If you wish to renew, renegotiate,
                   or cancel this contract. Please do so before that date."""


def get_latest_sdn_date() -> Optional[date]:
    return OFACSpeciallyDesignatedNational.objects.aggregate(Max("created_at")).get("created_at__max")


def find_sdns_by_name(db_search: str, fuzzy_search: str, date: date) -> list[OFACSpeciallyDesignatedNational]:
    if not db_search or not fuzzy_search or not date:
        raise TypeError()

    # Look at sdn.name and sdn.alternates.alt_name
    sdn_hits = (
        OFACSpeciallyDesignatedNational.objects.select_related()
        .filter(created_at=date, name__icontains=db_search)
        .all()
    )
    sdn_matches = [hit for hit in sdn_hits if get_search_ratio(fuzzy_search, hit.name)]

    # Look at sdn.alternates.alt_name
    alt_hits = OFACSpeciallyDesignatedNationalAlternate.objects.filter(
        created_at=date, alt_name__icontains=db_search
    ).values("sdn_id", "alt_name")
    alt_sdn_ids = [hit["sdn_id"] for hit in alt_hits if get_search_ratio(fuzzy_search, hit["alt_name"])]
    alt_matches = list(OFACSpeciallyDesignatedNational.objects.select_related().filter(pk__in=alt_sdn_ids))

    return sdn_matches + alt_matches


def find_sdns_by_address(db_search: str, fuzzy_search: str, date: date) -> list[OFACSpeciallyDesignatedNational]:
    if not db_search or not fuzzy_search or not date:
        raise TypeError()

    # Look at sdn.name and sdn.alternates.alt_name
    hits = (
        OFACSpeciallyDesignatedNationalAddress.objects.filter(created_at=date)
        .filter(address__icontains=db_search)
        .values("sdn_id", "address")
    )
    sdn_ids = [hit["sdn_id"] for hit in hits if get_search_ratio(fuzzy_search, hit["address"])]
    results = list(OFACSpeciallyDesignatedNational.objects.select_related().filter(pk__in=sdn_ids))
    return results


def find_sdns_by_vendor(vendor: Vendor, date: date) -> list[OFACSpeciallyDesignatedNational]:
    if not vendor or not date:
        raise TypeError()

    results: list[OFACSpeciallyDesignatedNational] = []
    if vendor.legal_name:
        db_search = vendor.legal_name.split(" ")[0]
        fuzzy_search = vendor.legal_name.split(",")[0]
        results.extend(find_sdns_by_name(db_search, fuzzy_search, date))

    if vendor.name:
        db_search = vendor.name.split(" ")[0]
        fuzzy_search = vendor.name
        results.extend(find_sdns_by_name(db_search, fuzzy_search, date))

    return results


def find_sdns_by_contact(contact: Contact, date: date) -> list[OFACSpeciallyDesignatedNational]:
    if not contact or not date:
        raise TypeError()

    results: list[OFACSpeciallyDesignatedNational] = []
    if contact.last_name:
        db_search = contact.last_name
        fuzzy_search = f"{contact.first_name} {contact.last_name}".strip()
        results.extend(find_sdns_by_name(db_search, fuzzy_search, date))

        fuzzy_search = f"{contact.last_name}, {contact.first_name}".strip()
        results.extend(find_sdns_by_name(db_search, fuzzy_search, date))

    if contact.line_1:
        words = contact.line_1.split(" ")
        db_search = words[1] if len(words) > 1 else words[0]
        fuzzy_search = contact.line_1
        results.extend(find_sdns_by_address(db_search, fuzzy_search, date))

    return results


def get_unique_sdns(sdns: list[OFACSpeciallyDesignatedNational]) -> list[OFACSpeciallyDesignatedNational]:
    return list({sdn.ent_num: sdn for sdn in sdns}.values())


def create_ofacresult_from_sdn(
    sdn: OFACSpeciallyDesignatedNational, vendor: Vendor = None, contact: Contact = None
) -> OFACSDNResult:
    if not sdn or (not vendor and not contact):
        raise TypeError

    aliases = sdn.ofacspeciallydesignatednationalalternate_set.all()
    addresses = sdn.ofacspeciallydesignatednationaladdress_set.all()

    # add vendor and contact ids to improve uniqueness of payload and hash
    contact_id = None
    vendor_id = None
    if vendor:
        vendor_id = vendor.id
    elif contact:
        contact_id = contact.id
        vendor_id = contact.vendor.id

    payload = {
        "ContactId": contact_id,
        "VendorId": vendor_id,
        "Number": sdn.ent_num,
        "Name": sdn.name,
        "Title": sdn.title,
        "Remarks": sdn.remarks,
        "Aliases": [
            {
                "AltName": item.alt_name,
                "Remarks": item.alt_remarks,
            }
            for item in aliases
        ],
        "Addresses": [
            {
                "Address": item.address,
                "Address2": item.address_line_2,
                "County": item.country,
                "Remarks": item.add_remarks,
            }
            for item in addresses
        ],
    }

    json_payload = json.dumps(payload).encode("utf-8")
    result = OFACSDNResult(
        total_sdn=1,
        total_address=len(addresses),
        total_alias=len(aliases),
        vendor=vendor,
        contact=contact,
        result=payload,
        hash_code=hashlib.md5(json_payload).hexdigest(),
    )

    return result


def save_new_ofac_results(results: list[OFACSDNResult]) -> list[OFACSDNResult]:
    hashes = [item.hash_code for item in results]
    existing = [item["hash_code"] for item in OFACSDNResult.objects.filter(hash_code__in=hashes).values("hash_code")]

    remaining = [item for item in results if item.hash_code not in existing]
    OFACSDNResult.objects.bulk_create(remaining)
    return remaining


def remove_duplicate_results(results: list[OFACSDNResult]) -> list[OFACSDNResult]:
    hashes = [item.hash_code for item in results]
    existing = [item["hash_code"] for item in OFACSDNResult.objects.filter(hash_code__in=hashes).values("hash_code")]
    remaining = [item for item in results if item.hash_code not in existing]
    return remaining


def vendor_search(vendor: Vendor = None, vendor_id: int = None, date: date = None):
    if not vendor and not vendor_id:
        raise TypeError()
    vendor = vendor or Vendor.objects.get(vendor_id)
    date = date or get_latest_sdn_date()
    sdn_hits = get_unique_sdns(find_sdns_by_vendor(vendor, date))
    results = [create_ofacresult_from_sdn(sdn, vendor) for sdn in sdn_hits]
    new_results = remove_duplicate_results(results)
    return new_results


def contact_search(contact: Contact = None, contact_id: int = None, date: date = None):
    if not contact and not contact_id:
        raise TypeError()

    contact = contact or Contact.objects.get(contact_id)
    date = date or get_latest_sdn_date()
    sdn_hits = get_unique_sdns(find_sdns_by_contact(contact, date))
    results = [create_ofacresult_from_sdn(sdn, contact=contact) for sdn in sdn_hits]
    new_results = remove_duplicate_results(results)
    return new_results


@shared_task(name="contract_renewal")
def contract_renewal():
    try:
        contracts = Contract.objects.filter(renewal_reminder_date__lte=date.today()).exclude(is_deleted=True)
        for contract in contracts:
            if contract.created_at.date() < contract.next_expiration:
                task_object = Task.objects.filter(
                    contract=contract, renewal_reminder_date=contract.renewal_reminder_date
                )
                if not task_object.exists():
                    task_object = Task.objects.create(
                        title=f"End of Contract - {contract.vendor.name}, {contract.title}",
                        description=get_description(contract),
                        linked_resources=contract.parent_contract.title if contract.parent_contract else None,
                        created_at=timezone.now(),
                        priority=TaskPriority.HIGH,  # High
                        status=TaskStatus.NOT_STARTED,  # Not started
                        owner=contract.vendor.owner,
                        contract=contract,
                        renewal_reminder_date=contract.renewal_reminder_date,
                        org=contract.vendor.org,
                    )
        # update status of contract
        contracts = Contract.objects.filter(next_expiration__lt=date.today(), is_auto_renew=False).exclude(
            is_deleted=True
        )
        for contract in contracts:
            contract.status = ContractStatus.TERMINATED
            contract.save()
    except Exception as e:
        logging.warning(str(e))


def get_task_description(hit):
    description = f"\nMatch Type: (SDN NAME ({hit.total_sdn}), ADDRESSES ({hit.total_address}), ALIASES ({hit.total_alias}))\nNumber: {hit.result['Number']} \nName: {hit.result['Name']} \nTitle: {hit.result['Title']} \nRemarks: {hit.result['Remarks']} \n\n"

    address = "---Addresses---\n\n"
    for add in hit.result["Addresses"]:
        address = (
            address
            + f"Address: {add['Address']}\nAddress2: {add['Address2']}\nCounty: {add['County']}\nRemarks: {add['Remarks']}\n\n"
        )
    aliases = "---Alases---\n\n"
    for alias in hit.result["Aliases"]:
        aliases = aliases + f"AltName: {alias['AltName']}\nRemarks: {alias['Remarks']}\n\n"
    description = description + address + aliases
    return description


@shared_task(name="vendor_report")
def vendor_report(vendor_id=None):
    vendors = Vendor.objects.exclude(ignore_sdn=True)
    if vendor_id:
        vendors = vendors.filter(id=vendor_id)

    for vendor in vendors:
        search_results = vendor_search(vendor)
        if search_results:
            OFACSDNResult.objects.bulk_create(search_results)
            tasks = [
                Task(
                    title=SDN_TASK_TITLE % (vendor.name),
                    description=(SDN_TASK_DESCRIPTION % (vendor.name) + "\n" + get_task_description(hit)).strip(),
                    linked_resources=vendor.name,
                    priority=TaskPriority.HIGH,  # High
                    status=TaskStatus.NOT_STARTED,  # Not Started
                    owner=vendor.owner,
                    org=vendor.org,
                    vendor=vendor,
                    ofac_result_id=hit.id,
                )
                for hit in search_results
                if not Task.objects.filter(vendor=vendor, ofac_result_id=hit.id)
            ]
            Task.objects.bulk_create(tasks)
            logger_object = ScheduledJobLogger.objects.create(
                api_url="OFAC", email=vendor.name, response_code="200", job_type="OFAC"
            )
            logger_object.save()


@shared_task(name="contact_report")
def contact_report(contact_id=None):
    contacts = Contact.objects.exclude(is_deleted=True)
    if contact_id:
        contacts = contacts.filter(id=contact_id).exclude(is_deleted=True)

    for contact in contacts:
        search_results = contact_search(contact=contact)
        if search_results:
            OFACSDNResult.objects.bulk_create(search_results)
            tasks = [
                Task(
                    title=SDN_TASK_TITLE % (f"{contact.vendor.name}, {contact.first_name} {contact.last_name}"),
                    description=(
                        SDN_TASK_DESCRIPTION % (f"{contact.first_name} {contact.last_name}")
                        + "\n"
                        + get_task_description(hit)
                    ).strip(),
                    linked_resources=f"{contact.first_name} {contact.last_name}",
                    priority=TaskPriority.HIGH,  # High
                    status=TaskStatus.NOT_STARTED,  # Not Started
                    owner=contact.vendor.owner,
                    org=contact.vendor.org,
                    vendor=contact.vendor,
                    contact=contact,
                    ofac_result_id=hit.id,
                )
                for hit in search_results
                if not Task.objects.filter(vendor=contact.vendor, ofac_result_id=hit.id)
            ]
            Task.objects.bulk_create(tasks)
            logger_object = ScheduledJobLogger.objects.create(
                api_url="OFAC", email=contact.email, response_code="200", job_type="OFAC"
            )
            logger_object.save()


@shared_task
def send_contract_status(user_id):
    user = User.objects.filter(pk=user_id).first()
    data = get_contract_activity(user)
    template_id = "d-180102e73d7549bf8cad64f725fe9dd5"
    payload = {
        "firstName": user.first_name if user.first_name else user.email,
        "num30": data["next_30"],
        "num31-60": data["next_60"],
        "num61-90": data["next_90"],
        "numExpired": data["last_30_no_renew"],
        "numAutorenewed": data["renewals"],
        "currentDate": timezone.now().date().strftime("%m/%d/%Y"),
    }
    email_service.delay(user.email, payload, template_id)


@shared_task(name="contract_status_email")
def contract_status_email():
    try:
        user_object = User.objects.all()
        for user in user_object:
            send_contract_status.delay(user.id)
    except Exception as e:
        logging.warning(str(e))


@shared_task(name="user_cleanup")
def user_cleanup():
    try:
        token_object = SurveyToken.objects.filter(expiration_date__date__lt=date.today())
        for token in token_object:
            user_object = User.objects.filter(pk=token.user.pk)
            user_object.delete()
        token_object.delete()
    except Exception as e:
        logging.warning(str(e))
