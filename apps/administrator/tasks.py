import csv
import logging
from datetime import date

import requests
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from apps.tasks.models import Task, TaskPriority, TaskStatus
from core.settings.local import (
    OFAC_SDN_ADDRESS_CSV_URL,
    OFAC_SDN_ALT_CSV_URL,
    OFAC_SDN_CSV_URL,
)

from .models import (
    Location,
    OFACSDNResult,
    OFACBase,
    OFACSpeciallyDesignatedNational,
    OFACSpeciallyDesignatedNationalAddress,
    OFACSpeciallyDesignatedNationalAlternate,
    ScheduledJobLogger,
)
from apps.utility.VendorUtilities import get_contract_activity, get_search_ratio
from typing import Optional
from django.db.models import Max
import json
import hashlib

INVALID_ROW = "\x1a"
SDN_TASK_TITLE = "Possible OFAC Hit - %s"
SDN_TASK_DESCRIPTION = "We found a match between %s and \
someone on the OFAC list.  Please click here \
https://sanctionssearch.ofac.treas.gov/ to research this person \
further."

def get_data(data):
    return data if data != "-0- " else ""


def download_ofac_file(url: str) -> list[str]:
    response = requests.get(url)
    content = response.content.decode()
    return content.splitlines()


def download_ofac_alternate_file() -> list[str]:
    return download_ofac_file(OFAC_SDN_ALT_CSV_URL)


def download_ofac_address_file() -> list[str]:
    return download_ofac_file(OFAC_SDN_ADDRESS_CSV_URL)


def download_ofac_sdn_file() -> list[str]:
    return download_ofac_file(OFAC_SDN_CSV_URL)


def clear_existing_ofac_entries(date: date):
    OFACSpeciallyDesignatedNational.objects.filter(created_at=date).delete()


def import_ofac_sdn_list(date: date, data: list[str]) -> int:
    source_reader = csv.reader(data)
    items = [
        OFACSpeciallyDesignatedNational(
            id=OFACBase.get_surrogate_key(date, get_data(row[0])),
            created_at=date,
            ent_num=get_data(row[0]),
            name=get_data(row[1]),
            sdn_type=get_data(row[2]),
            program=get_data(row[3]),
            title=get_data(row[4]),
            call_sign=get_data(row[5]),
            vess_type=get_data(row[6]),
            tonnage=get_data(row[7]),
            grt=get_data(row[8]),
            vess_flag=get_data(row[9]),
            vess_owner=get_data(row[10]),
            remarks=get_data(row[11]),
        )
        for row in source_reader
        if row[0] != INVALID_ROW
    ]
    OFACSpeciallyDesignatedNational.objects.bulk_create(items)
    return len(items)


def import_ofac_address_list(date: date, data: list[str]) -> int:
    source_reader = csv.reader(data)
    items = [
        OFACSpeciallyDesignatedNationalAddress(
            id=OFACBase.get_surrogate_key(date, get_data(row[1])),
            sdn_id=OFACBase.get_surrogate_key(date, get_data(row[0])),
            created_at=date,
            ent_num=get_data(row[0]),
            add_num=get_data(row[1]),
            address=get_data(row[2]),
            address_line_2=get_data(row[3]),
            country=get_data(row[4]),
            add_remarks=get_data(row[5]),
        )
        for row in source_reader
        if row[0] != INVALID_ROW
    ]

    # strip out any addresses that contain no real data
    items = [item for item in items if item.address or item.address_line_2 or item.country or item.add_remarks]

    # save the rest
    OFACSpeciallyDesignatedNationalAddress.objects.bulk_create(items)
    return len(items)


def import_ofac_alternate_list(date: date, data: list[str]) -> int:
    source_reader = csv.reader(data)
    items = [
        OFACSpeciallyDesignatedNationalAlternate(
            id=OFACBase.get_surrogate_key(date, get_data(row[1])),
            sdn_id=OFACBase.get_surrogate_key(date, get_data(row[0])),
            created_at=date,
            ent_num=get_data(row[0]),
            alt_num=get_data(row[1]),
            alt_type=get_data(row[2]),
            alt_name=get_data(row[3]),
            alt_remarks=get_data(row[4]),
        )
        for row in source_reader
        if row[0] != INVALID_ROW
    ]
    OFACSpeciallyDesignatedNationalAlternate.objects.bulk_create(items)
    return len(items)


@shared_task(name="fetch_weekly_ofac_list")
@transaction.atomic()
def fetch_weekly_ofac_list():
    try:
        date = timezone.now().date()
        clear_existing_ofac_entries(date)
        import_ofac_sdn_list(date, download_ofac_sdn_file())
        import_ofac_address_list(date, download_ofac_address_file())
        import_ofac_alternate_list(date, download_ofac_alternate_file())
    except Exception as e:
        logging.exception("OFAC Import failed")
        raise


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


def find_sdns_by_location(location: Location, date: date) -> list[OFACSpeciallyDesignatedNational]:
    if not location or not date:
        raise TypeError()
    results: list[OFACSpeciallyDesignatedNational] = []

    if location.line_1:
        words = location.line_1.split(" ")
        db_search = words[1] if len(words) > 1 else words[0]
        fuzzy_search = location.line_1
        results.extend(find_sdns_by_address(db_search, fuzzy_search, date))

    if location.name:
        db_search = location.name.split(" ")[0]
        fuzzy_search = location.name
        results.extend(find_sdns_by_name(db_search, fuzzy_search, date))

    return results
    

def get_unique_sdns(sdns: list[OFACSpeciallyDesignatedNational]) -> list[OFACSpeciallyDesignatedNational]:
    return list({sdn.ent_num: sdn for sdn in sdns}.values())


def create_ofacresult_from_sdn(
    sdn: OFACSpeciallyDesignatedNational, location: Location = None
) -> OFACSDNResult:
    if not sdn or (not location):
        raise TypeError

    aliases = sdn.ofacspeciallydesignatednationalalternate_set.all()
    addresses = sdn.ofacspeciallydesignatednationaladdress_set.all()

    # add vendor and contact ids to improve uniqueness of payload and hash
    # contact_id = None
    location_id = None
    if location:
        location_id = location.id


    payload = {
        "LocationId": location_id,
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
        location=location,
        result=payload,
        hash_code=hashlib.md5(json_payload).hexdigest(),
    )
    return result


def remove_duplicate_results(results: list[OFACSDNResult]) -> list[OFACSDNResult]:
    hashes = [item.hash_code for item in results]
    existing = [item["hash_code"] for item in OFACSDNResult.objects.filter(hash_code__in=hashes).values("hash_code")]
    remaining = [item for item in results if item.hash_code not in existing]
    return remaining


def location_search(location: Location = None, location_id: int = None, date: date = None):
    if not location and not location_id:
        raise TypeError()
    location = location or Location.objects.get(location_id)
    date = date or get_latest_sdn_date()
    sdn_hits = get_unique_sdns(find_sdns_by_location(location, date))
    results = [create_ofacresult_from_sdn(sdn, location) for sdn in sdn_hits]
    new_results = remove_duplicate_results(results)
    return new_results


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


@shared_task(name="location_report")
def location_report(location_id=None):
    locations = Location.objects.exclude(ignore_sdn=True)
    if location_id:
        locations = locations.filter(id=location_id)

    for location in locations:
        search_results = location_search(location)
        if search_results:
            OFACSDNResult.objects.bulk_create(search_results)
            tasks = [
                Task(
                    title=SDN_TASK_TITLE % (location.name),
                    description=(SDN_TASK_DESCRIPTION % (location.name) + "\n" + get_task_description(hit)).strip(),
                    linked_resources=location.name,
                    priority=TaskPriority.HIGH,  # High
                    status=TaskStatus.NOT_STARTED,  # Not Started
                    org=location.org,
                    location=location,
                    ofac_result_id=hit.id,
                )
                for hit in search_results
                if not Task.objects.filter(location=location, ofac_result_id=hit.id)
            ]
            Task.objects.bulk_create(tasks)
            logger_object = ScheduledJobLogger.objects.create(
                api_url="OFAC", email=location.name, response_code="200", job_type="OFAC"
            )
            logger_object.save()