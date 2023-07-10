from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.db.models import Count, QuerySet, Sum
from organizations.models import Organization, OrganizationUser
from thefuzz import fuzz
import re
from apps.vendor.models import Contract, Vendor
from apps.authentication.models import User
import re

SEARCH_MINE = "mine"


def org_users(user):
    org_user = OrganizationUser.objects.filter(user=user)
    users = (
        User.objects.filter(organizations_organization=org_user.first().organization, is_invited=False)
        .exclude(email__endswith="_gracen@gmail.com")
        .values("first_name", "last_name", "id", "email")
    )
    return list(users)


def org_vendors(user: AbstractUser) -> QuerySet:
    """get all vendors associated to user's org"""
    # If the user is None, has no ID or is not active
    # return an empty queryset
    if not user or not user.id or not user.is_active:
        return Vendor.objects.none()

    # find only orgs that the user is associated to and that
    # are active
    orgs = [
        o.organization
        for o in OrganizationUser.objects.filter(user_id=user.id).select_related("organization")
        if o.organization.is_active
    ]
    return Vendor.objects.filter(org__in=orgs)


def get_contract_activity(user: AbstractUser, search: str = None):
    """get contarct activity for dashboards"""
    today = timezone.now().date()
    next_30 = [today, today + timedelta(days=30)]
    next_60 = [today + timedelta(days=31), today + timedelta(days=60)]
    next_90 = [today + timedelta(days=61), today + timedelta(days=90)]
    last_30 = [today + timedelta(days=-30), today]

    models = org_vendors(user)
    if search == SEARCH_MINE:
        models = org_vendors(user).filter(owner=user)
    expiring_next_30 = Contract.objects.filter(
        vendor__in=models, superseded_by=None, next_expiration__range=next_30
    ).exclude(is_deleted=True)
    expiring_next_60 = Contract.objects.filter(
        vendor__in=models, superseded_by=None, next_expiration__range=next_60
    ).exclude(is_deleted=True)
    expiring_next_90 = Contract.objects.filter(
        vendor__in=models, superseded_by=None, next_expiration__range=next_90
    ).exclude(is_deleted=True)
    expired_last_30 = Contract.objects.filter(
        vendor__in=models, superseded_by=None, next_expiration__range=last_30, is_auto_renew=False
    ).exclude(is_deleted=True)
    renewals = Contract.objects.filter(
        vendor__in=models, superseded_by=None, is_auto_renew=True, next_expiration__range=last_30
    ).exclude(is_deleted=True)
    expired_last_30_no_renew = Contract.objects.filter(
        vendor__in=models, superseded_by=None, next_expiration__range=last_30, is_auto_renew=False
    ).exclude(is_deleted=True)

    return {
        "next_30": expiring_next_30.count(),
        "next_60": expiring_next_60.count(),
        "next_90": expiring_next_90.count(),
        "last_30": expired_last_30.count(),
        "renewals": renewals.count(),
        "last_30_no_renew": expired_last_30_no_renew.count(),
        "next_30_contract": expiring_next_30,
        "next_60_contract": expiring_next_60,
        "next_90_contract": expiring_next_90,
        "last_30_contract": expired_last_30,
        "renewals_contract": renewals,
        "last_30_no_renew_contract": expired_last_30_no_renew,
    }


def get_search_ratio(val1, val2):
    return fuzz.ratio(val1.lower(), val2.lower()) >= 80


def find_urls(string):
    # regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    # regex = r"/^((ftp|http|https):\/\/)?(www.)?(?!.*(ftp|http|https|www.))[a-zA-Z0-9_-]+(\.[a-zA-Z]+)+((\/)[\w#]+)*(\/\w+\?[a-zA-Z0-9_]+=\w+(&[a-zA-Z0-9_]+=\w+)*)?\/?$/gm"

    regex = re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    url = re.findall(regex, string)
    return url


def get_linked_text(org_str):
    original_str = org_str.strip()
    original_str = original_str.replace("&nbsp;", " ")
    for i in original_str.split(" "):
        i = i.strip()
        if (i.endswith("<div>")) or (i.startswith("</div>")) or (i.endswith("</div>")) or (i.startswith("<div>")):
            i = i.replace("<div>", " ")
            i = i.replace("</div>", " ")
            i = i.replace("<br>", " ")
            new_str = i.split()
            for i in new_str:
                if i in find_urls(i):
                    original_str = original_str.replace(i, f"<a contenteditable=false target=_blank href={i}>{i}</a> ")
        else:
            if i in find_urls(i):
                original_str = original_str.replace(i, f"<a contenteditable=false target=_blank href={i}>{i}</a> ")
    return original_str


def get_mention_user(notes):
    note = notes.split(" ")
    users = []
    for i in note:
        if i.startswith("id"):
            temp = re.findall(r"\d+", i)
            users = users + list(map(int, temp))
    return list(set(users))
