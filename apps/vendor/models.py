# -*- encoding: utf-8 -*-
"""vendor models module"""
import math
from datetime import timedelta
from operator import itemgetter

import phonenumbers
from django.core.validators import MaxLengthValidator, RegexValidator
from django.db import models
from django.db.models.deletion import CASCADE, SET_NULL
from django.db.models.fields import (
    BooleanField,
    CharField,
    DateField,
    EmailField,
    IntegerField,
    TextField,
)
from django.db.models.fields.files import FileField
from django.db.models.fields.related import ForeignKey, OneToOneField
from django.db.models.functions import Length
from django.db.models.query_utils import Q
from organizations.models import Organization
from phonenumber_field.modelfields import PhoneNumberField
from simple_history.models import HistoricalRecords

from apps.authentication.models import User as AuthUser
from django.core.files.storage import default_storage
from django.utils.html import strip_tags
from apps.djf_surveys.models import *
from django.utils.translation import gettext_lazy as _
from pytz import timezone as time_zone
from apps.djf_surveys.models import BaseSurveyModel, BaseQuestionModel, SurveyStatus
from django.utils import timezone
from core.settings.base import QUESTIONNAIRE_INVITATION_TTL
import uuid
from django.db.models import Q

CharField.register_lookup(Length, "length")

VENDOR_STATUS_DISPLAYNAMES = {
    1: "Proposal",
    "PROPOSAL": "Proposal",
    2: "Active",
    "ACTIVE": "Active",
    3: "Terminated",
    "TERMINATED": "Terminated",
    4: "Not Engaged",
    "NOT_ENGAGED": "Not Engaged",
}

RISK_GRADE_DISPLAYNAMES = {
    0: "None",
    "NONE": "None",
    1: "Low",
    "LOW": "Low",
    2: "Medium",
    "MEDIUM": "Medium",
    3: "High",
    "HIGH": "High",
}

LEGAL_STRUCTURE_DISPLAYNAMES = {
    0: "Sole Proprietorship",
    "SOLE_PROPRIETORSHIP": "Sole Proprietorship",
    1: "General Partnership",
    "GENERAL_PARTNERSHIP": "General Partnership",
    2: "Limited Partnership",
    "LIMITED_PARTNERSHIP": "Limited Partnership",
    3: "Limited Liability Corporation",
    "LIMITED_LIABILITY_CORPORATION": "Limited Liability Corporation",
    4: "C Corporation",
    "C_CORPORATION": "C Corporation",
    5: "S Corporation",
    "S_CORPORATION": "S Corporation",
}


# Create your models here.
class Criticality(models.IntegerChoices):
    """known criticallities"""

    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


class LegalStructure(models.IntegerChoices):
    """known legal structures"""

    SOLE_PROPRIETORSHIP = 0
    GENERAL_PARTNERSHIP = 1
    LIMITED_PARTNERSHIP = 2
    LIMITED_LIABILITY_CORPORATION = 3
    C_CORPORATION = 4
    S_CORPORATION = 5


class RiskGrade(models.IntegerChoices):
    """known risk grades"""

    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class ContactType(models.IntegerChoices):
    """known contact types"""

    OTHER = 0
    HEADQUARTERS = 1
    PRIMARY = 2
    LEGAL = 3
    ACCOUNTING = 4
    TECHNICAL = 5


class PhoneType(models.IntegerChoices):
    """known phone types"""

    OTHER = 0
    MAIN = 1
    OFFICE = 2
    CELL = 3
    HOME = 4
    FAX = 5


class VendorStatus(models.IntegerChoices):
    """known proposal types"""

    PROPOSAL = 1
    ACTIVE = 2
    TERMINATED = 3
    NOT_ENGAGED = 4


class ContactRole(models.IntegerChoices):
    """known contact roles"""

    SALES_EXECUTIVE = 1
    ACCOUNT_MANAGER = 2
    LEGAL = 3
    ACCOUNTING = 4
    TECHNOLOGY = 5
    OPERATIONS = 6
    PRIMARY_BUSINESS_ADDRESS = 7


class ContractStatus(models.IntegerChoices):
    PRE_CONTRACT = 1
    ACTIVE = 2
    TERMINATED = 3
    NOT_EXECUTED = 4


class RankField(models.IntegerChoices):
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3


def get_contract_status(status):
    status = int(status)
    if status == 1:
        return "Pre-contract"
    elif status == 2:
        return "Active"
    elif status == 3:
        return "Terminated"
    elif status == 4:
        return "Not Executed"
    return ""


def get_risk(risk):
    if not risk:
        return RiskGrade.NONE
    elif risk.lower() == "low":
        return RiskGrade.LOW
    elif risk.lower() == "medium":
        return RiskGrade.MEDIUM
    elif risk.lower() == "high":
        return RiskGrade.HIGH
    else:
        return RiskGrade.NONE


def get_status(status):
    if not status:
        return None
    elif status.lower() == "active":
        return VendorStatus.ACTIVE
    elif status.lower() == "proposal":
        return VendorStatus.PROPOSAL
    elif status.lower() == "terminated":
        return VendorStatus.TERMINATED
    elif status.lower() == "not engaged":
        return VendorStatus.NOT_ENGAGED
    else:
        return None


# def add_org_business_process(value, org):
#     value = value.split("-")
#     from apps.administrator.models import BusinessUnit, Department, Process

#     units = None
#     departments = None
#     processes = None
#     if len(value) == 3:
#         units = BusinessUnit.objects.filter(organization=org, name=value[0]).exclude(is_deleted=True).first()
#         if not units:
#             units = BusinessUnit.objects.create(organization=org, name=value[0])
#     if len(value) >= 2:
#         departments = (
#             Department.objects.filter(organization=org, name=value[1] if len(value) == 3 else value[0])
#             .exclude(is_deleted=True)
#             .first()
#         )
#         if not departments:
#             departments = Department.objects.create(
#                 unit=units, organization=org, name=value[1] if len(value) == 3 else value[0]
#             )
#     if len(value) >= 1:
#         name = value[0]
#         if len(value) == 3:
#             name = value[2]
#         elif len(value) == 2:
#             name = value[1]
#         processes = Process.objects.filter(organization=org, name=name).exclude(is_deleted=True)
#         if not processes.exists():
#             processes = Process.objects.create(department=departments, organization=org, name=name)


class Vendor(models.Model):
    """vendor model"""

    org = ForeignKey(Organization, on_delete=CASCADE)
    name = CharField(max_length=1024)
    legal_name = CharField(max_length=1024, null=True, blank=True)
    legal_structure = IntegerField(choices=LegalStructure.choices, null=True, blank=True)
    is_offshore = BooleanField(default=False)
    critical = models.BooleanField(default=False)
    inherent_risk = IntegerField(choices=RiskGrade.choices, default=0)
    residual_risk = IntegerField(choices=RiskGrade.choices, default=0)
    category = CharField(max_length=1024, null=True, blank=True)
    org_business_process = ForeignKey("administrator.BusinessProcess", on_delete=SET_NULL , null=True, blank=True)
    owner = ForeignKey(AuthUser, on_delete=SET_NULL, null=True, blank=True)
    status = IntegerField(choices=VendorStatus.choices, null=True, blank=True)
    time_for_renewal = DateField(editable=False, null=True, blank=True)
    tax_id_number = CharField(
        max_length=11,
        null=True,
        blank=True,
        validators=[
            RegexValidator(r"^\d{2}-\d{7}$|^\d{3}-\d{2}-\d{4}$", "Expected format: 12-1234567 or 123-45-6789."),
        ],
    )
    website = CharField(max_length=1024, null=True, blank=True)
    twitter = CharField(max_length=1024, null=True, blank=True)
    linkedin = CharField(max_length=1024, null=True, blank=True)
    facebook = CharField(max_length=1024, null=True, blank=True)
    stock_symbol = CharField(max_length=1024, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    ignore_sdn = models.BooleanField(default=False)
    risk_type = models.CharField(max_length=1000, null=True, blank=True)
    risk_description = models.TextField(null=True, blank=True)
    history = HistoricalRecords()
    vendor_optional_id = models.CharField(max_length=1024, blank=True, null=True)
    rank = models.IntegerField(choices=RankField.choices, null=True, blank=True)

    @property
    def get_risk_description(self):
        from apps.utility.VendorUtilities import get_linked_text

        if self.risk_description:
            return get_linked_text(self.risk_description)
        else:
            return ""

    @property
    def get_notes(self):
        from apps.utility.VendorUtilities import get_linked_text

        if self.notes:
            return get_linked_text(self.notes)
        else:
            return ""

    def get_history(self):
        history_object = self.history.all().exclude(history_type="Created").order_by("history_date")
        history_str = ""
        for data in history_object:
            if data.next_record:
                delta = data.next_record.diff_against(data)
                if delta.changes:
                    author = ""
                    if data.next_record.history_user:
                        if data.next_record.history_user:
                            author = (
                                f"{data.next_record.history_user.first_name} {data.next_record.history_user.last_name}"
                            ).capitalize()
                        else:
                            author = ""
                    history_str = (
                        history_str
                        + f"<h6 class='mb-0 mt-2' style='color:black;'>{str(data.next_record.history_date.astimezone(time_zone('US/Pacific')).strftime('%m/%d/%y %I:%M %p'))} - {author}</h6>"
                    )
                    for change in delta.changes:
                        if change.field == "time_for_renewal":
                            pre_value = change.old.strftime("%m/%d/%y") if change.old else ""
                            value = change.new.strftime("%m/%d/%y") if change.new else ""
                        elif change.field == "legal_structure":
                            pre_value = LEGAL_STRUCTURE_DISPLAYNAMES[change.old] if change.old else "None"
                            value = LEGAL_STRUCTURE_DISPLAYNAMES[change.new] if change.new else "None"
                        elif change.field == "status":
                            pre_value = VENDOR_STATUS_DISPLAYNAMES[change.old] if change.old else "None"
                            value = VENDOR_STATUS_DISPLAYNAMES[change.new] if change.new else "None"
                        elif change.field in ["inherent_risk", "residual_risk"]:
                            pre_value = RISK_GRADE_DISPLAYNAMES[change.old] if change.old else "None"
                            value = RISK_GRADE_DISPLAYNAMES[change.new] if change.new else "None"
                        elif change.field in ["is_offshore", "critical", "ignore_sdn"]:
                            pre_value = "Yes" if change.old else "No"
                            value = "Yes" if change.new else "No"
                        elif change.field in ["notes", "risk_description"]:
                            pre_value = strip_tags(change.old).replace("&nbsp;", " ").strip() if change.old else ""
                            value = strip_tags(change.new).replace("&nbsp;", " ").strip() if change.new else ""
                        elif change.field == "owner":
                            value = ""
                            pre_value = ""
                            if change.new:
                                owner_object = AuthUser.objects.filter(pk=change.new).first()
                                if owner_object:
                                    value = f"{owner_object.first_name} {owner_object.last_name}"
                            if change.old:
                                owner_object = AuthUser.objects.filter(pk=change.old).first()
                                if owner_object:
                                    pre_value = f"{owner_object.first_name} {owner_object.last_name}"
                        else:
                            pre_value = str(change.old).strip() if change.old else ""
                            value = str(change.new).strip() if change.new else ""
                        history_str = history_str + "<h5 class='history-text'><span style='text-decoration:underline'>{}</span>: {}  <span style='font-weight:bold'>--></span>  {}</h5>".format(
                            (change.field).replace("_", " ").capitalize(),
                            pre_value,
                            value,
                        )
        return history_str

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["org", "tax_id_number"],
                condition=Q(tax_id_number__isnull=False),
                name="tax_id_number_unique_within_org",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super(Vendor, self).save(*args, **kwargs)
        # if self.org_business_process:
        #     add_org_business_process(self.org_business_process, self.org)


class Contact(models.Model):
    """contact model"""

    vendor = ForeignKey(Vendor, on_delete=CASCADE)
    first_name = CharField(max_length=1024)
    last_name = CharField(max_length=1024)
    email = EmailField(max_length=1024, null=True, blank=True)
    line_1 = CharField(max_length=1024, null=True, blank=True)
    line_2 = CharField(max_length=1024, null=True, blank=True)
    city = CharField(max_length=1024, null=True, blank=True)
    state = CharField(max_length=2, null=True, blank=True)
    zip_code = CharField(max_length=9, null=True, blank=True)
    role = IntegerField(choices=sorted(ContactRole.choices, key=itemgetter(1)), null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    ignore_sdn = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.last_name + ", " + self.first_name

    @property
    def get_notes(self):
        from apps.utility.VendorUtilities import get_linked_text

        if self.notes:
            return get_linked_text(self.notes)
        return ""


class Phone(models.Model):
    """phone model"""

    contact = ForeignKey(Contact, on_delete=CASCADE)
    number = PhoneNumberField()
    type = IntegerField(choices=PhoneType.choices, null=True, blank=True)
    is_preferred = BooleanField()
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return phonenumbers.format_number(
            self.number,
            phonenumbers.PhoneNumberFormat.NATIONAL,
        )


class Contract(models.Model):
    """contract model"""

    vendor = ForeignKey(Vendor, on_delete=CASCADE)
    title = CharField(max_length=1024)
    effective_date = DateField(null=True, blank=True)
    next_expiration = DateField(null=True, blank=True)
    renewal_period_days = IntegerField(null=True, blank=True)
    terms = TextField(max_length=4096, blank=True, null=True, validators=[MaxLengthValidator(4096)])
    renewal_pad = IntegerField(null=True, blank=True)
    renewal_reminder_date = DateField(editable=False, null=True, blank=True)
    history = HistoricalRecords()
    superseded_by = OneToOneField("self", null=True, blank=True, on_delete=CASCADE, related_name="supersedes")
    is_auto_renew = BooleanField(default=False)
    parent_contract = ForeignKey("self", on_delete=SET_NULL, null=True, blank=True, related_name="child_contracts")
    is_deleted = models.BooleanField(default=False)
    has_minimum_fees = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    contract_optional_id = models.CharField(max_length=1024, blank=True, null=True)
    status = models.IntegerField(null=True, blank=True, choices=ContractStatus.choices)

    def save(self, *args, **kwargs):
        self.renewal_reminder_date = (
            self.next_expiration - timedelta(days=(self.renewal_period_days or 0) + (self.renewal_pad or 0))
            if self.next_expiration
            else None
        )

        super().save(*args, **kwargs)

        # RECALCULATING THE VENDOR TIME FOR RENEWAL ANYTIME A CHILD
        # CONTRACT IS ADDED, REMOVED, OR UPDATED SHOULD REALLY BE
        # A TRIGGER.
        #
        # MOVE TO TRIGGER CAN BE DONE ONCE ALL ENVS ARE USING THE SAME DB TYPE
        #
        # AS OF NOW DEV ENV IS CURRENTLY USING SQLITE AND OTHER ENVS ARE USING
        # POSTGRESQL
        contracts = self.vendor.contract_set.exclude(renewal_reminder_date=None).filter(superseded_by_id=None).all()
        nearest = (
            sorted(contracts, key=lambda x: x.renewal_reminder_date)[0].renewal_reminder_date if contracts else None
        )
        self.vendor.time_for_renewal = nearest
        self.vendor.save()

    class Meta:
        ordering = ["title"]
        constraints = [
            models.CheckConstraint(
                check=Q(parent_contract__isnull=True) | ~Q(parent_contract_id=models.F("id")),
                name="contract_cannot_reference_self",
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def get_terms(self):
        from apps.utility.VendorUtilities import get_linked_text

        if self.terms:
            return get_linked_text(self.terms)
        return ""

    @property
    def get_childs(self):
        return Contract.objects.filter(parent_contract_id=self.id).exclude(is_deleted=True)

    @property
    def get_child_count(self):
        return Contract.objects.filter(parent_contract_id=self.id).exclude(is_deleted=True).count()

    @property
    def get_seding_line(self):
        return self.superseded_by

    @property
    def get_draw_line(self):
        draw_line = Contract.objects.filter(parent_contract_id=self.id).exclude(is_deleted=True)
        if not draw_line:
            draw_line = self.superseded_by
        return draw_line

    @property
    def get_superseded_by(self):
        id_list = []
        data = self
        try:

            def get_superseded_by_list(data):
                if data.superseded_by:
                    id_list.append(data.superseded_by)
                    get_superseded_by_list(data.superseded_by)

            get_superseded_by_list(data)
            return id_list
        except Exception as e:
            return id_list

    @property
    def get_icon(self):

        icon = "check_circle"
        if self.superseded_by:
            icon = "highlight_off"
        elif Contract.objects.filter(superseded_by_id=self.id).exclude(is_deleted=True):
            icon = "check_circle"
        elif self.parent_contract:
            icon = "arrow_circle_right"
        return icon

    @property
    def get_line_height(self):
        height = 101
        height_count = 1
        parent = Contract.objects.filter(superseded_by_id=self.id).exclude(is_deleted=True).first()
        if self.superseded_by:
            childs = Contract.objects.filter(parent_contract=self).exclude(is_deleted=True)
            if len(childs) > 0:
                height_count = height_count + 1
                # if not child:
                #     height_count = height_count + 1

                for child in childs:
                    if child == parent:
                        break
                    child_of_child = Contract.objects.filter(parent_contract=child).exclude(is_deleted=True)
                    for nested_child in child_of_child:
                        if nested_child == parent:
                            break
                        height_count = height_count + 1
                        nest_seding = nested_child.superseded_by
                        while nest_seding:
                            height_count = height_count + 1
                            nest_seding = nest_seding.superseded_by
                    super_seded_by = child.superseded_by
                    while super_seded_by:
                        height_count = height_count + 1
                        childrens = Contract.objects.filter(parent_contract=super_seded_by).exclude(is_deleted=True)
                        for data in childrens:
                            if data == parent:
                                break
                            height_count = height_count + 1
                            child_seded = data.superseded_by
                            while child_seded:
                                height_count = height_count + 1
                                child_seded = child_seded.superseded_by
                        super_seded_by = super_seded_by.superseded_by
        height = height * height_count
        # if child:
        #     height = height + 10
        # else:
        #     height = height - 33
        return str(height) + "%"

    @property
    def get_level(self):
        level = 1
        parent = self
        count_for_parent = 0
        count_for_superseded = 0
        while parent:
            if parent.parent_contract:
                parent = parent.parent_contract
                count_for_parent += 1
                if count_for_parent == 1:
                    level = 2
                else:
                    level = 3
            elif Contract.objects.filter(superseded_by=parent).exclude(is_deleted=True):
                parent = Contract.objects.filter(superseded_by=parent).exclude(is_deleted=True).first()
            else:
                parent = None
        return level

    def get_history(self):
        history_object = self.history.all().exclude(history_type="Created").order_by("history_date")
        history_str = ""
        for data in history_object:
            if data.next_record:
                delta = data.next_record.diff_against(data)
                if delta.changes:
                    author = ""
                    if data.next_record.history_user:
                        author = (
                            f"{data.next_record.history_user.first_name} {data.next_record.history_user.last_name}"
                        ).capitalize()
                    history_str = (
                        history_str
                        + f"<h6 class='mb-0 mt-2' style='color:black;'>{str(data.next_record.history_date.astimezone(time_zone('US/Pacific')).strftime('%m/%d/%y %I:%M %p'))} - {author}</h6>"
                    )
                    for change in delta.changes:
                        if change.field in ["effective_date", "next_expiration", "renewal_reminder_date"]:
                            pre_value = change.old.strftime("%m/%d/%y") if change.old else ""
                            value = change.new.strftime("%m/%d/%y") if change.new else ""
                        elif change.field in ["is_auto_renew", "has_minimum_fees"]:
                            pre_value = "Yes" if change.old else "No"
                            value = "Yes" if change.new else "No"
                        elif change.field == "status":
                            pre_value = get_contract_status(change.old) if change.old else ""
                            value = get_contract_status(change.new) if change.new else ""
                        elif change.field in ["superseded_by", "parent_contract"]:
                            pre_value = Contract.objects.filter(pk=change.old).first().title if change.old else ""
                            value = Contract.objects.filter(pk=change.new).first().title if change.new else ""
                        elif change.field == "terms":
                            pre_value = strip_tags(change.old).replace("&nbsp;", " ").strip() if change.old else ""
                            value = strip_tags(change.new).replace("&nbsp;", " ").strip() if change.new else ""
                        else:
                            pre_value = str(change.old).strip() if change.old else ""
                            value = str(change.new).strip() if change.new else ""
                        history_str = history_str + "<h5 class='history-text'><span style='text-decoration:underline'>{}</span>: {}  <span style='font-weight:bold'>--></span>  {}</h5>".format(
                            (change.field).replace("_", " ").capitalize(),
                            pre_value,
                            value,
                        )
        return history_str


class Document(models.Model):
    """document model"""

    vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=CASCADE)
    contract = ForeignKey(Contract, on_delete=CASCADE, null=True, blank=True)
    name = CharField(max_length=1024)
    description = CharField(max_length=4096, null=True, blank=True)
    path = FileField(max_length=4096)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return self.name

    @property
    def created_date(self):
        return self.created_at.date

    @property
    def updated_date(self):
        if self.updated_at:
            return self.updated_at.date

    @property
    def file_exists(self):
        if default_storage.exists(self.path.name):
            return True
        else:
            return False


class VendorSurvey(BaseSurveyModel):
    vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=CASCADE)
    user = models.ForeignKey(AuthUser, null=True, blank=True, on_delete=CASCADE)
    survey = models.ForeignKey(
        OrgSurvey, related_name="survey", on_delete=models.SET_NULL, verbose_name=_("survey"), null=True, blank=True
    )
    due_date = models.DateField(null=True, blank=True)
    is_sent_by_org = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    is_sent_by_vendor = models.BooleanField(default=False)
    sent_date = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(AuthUser, null=True, blank=True, on_delete=CASCADE, related_name="sender")
    history = HistoricalRecords()
    invite_due_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = _("survey")
        verbose_name_plural = _("surveys")

    def __str__(self):
        return self.name

    @property
    def get_percentage(self):
        percentage = 0
        total_questions = VendorSurveyQuestion.objects.filter(survey=self).exclude(is_deleted=True).count()
        total_answers = (
            VendorSurveyAnswer.objects.filter(user_answer__survey=self)
            .exclude(question__type_field=10).exclude(question__is_deleted=True)
            .filter(~Q(value=None))
            .filter(~Q(value=""))
        )
        total_answers = total_answers.count()
        total_document_answers = (
            VendorSurveyAnswer.objects.filter(user_answer__survey=self).exclude(question__is_deleted=True)
            .filter(question__type_field=10)
            .filter(~Q(document=None) & ~Q(document=''))
            .count()
        )
        total_answers = total_answers + total_document_answers
        percentage = math.floor((total_answers / total_questions) * 100)
        return percentage

    def save(self, *args, **kwargs):
        if self.slug:
            self.slug = generate_unique_slug(VendorSurvey, self.slug, self.id)
        else:
            self.slug = generate_unique_slug(VendorSurvey, self.name, self.id)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("survey")
        verbose_name_plural = _("surveys")


class VendorSurveyQuestion(BaseQuestionModel):
    vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=CASCADE)
    survey = models.ForeignKey(
        VendorSurvey, related_name="questions", on_delete=models.CASCADE, verbose_name=_("survey")
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = _("question")
        verbose_name_plural = _("questions")
        ordering = ["ordering"]

    def __str__(self):
        return f"{self.label}-survey-{self.survey.id}"

    def save(self, *args, **kwargs):
        if self.key:
            self.key = generate_unique_slug(VendorSurveyQuestion, self.key, self.id, "key")
        else:
            self.key = generate_unique_slug(VendorSurveyQuestion, self.label, self.id, "key")

        super(VendorSurveyQuestion, self).save(*args, **kwargs)


class VendorSurveyUserAnswer(BaseModel):
    survey = models.ForeignKey(VendorSurvey, on_delete=models.CASCADE, verbose_name=_("survey"))
    vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=CASCADE)
    history = HistoricalRecords()

    class Meta:
        verbose_name = _("user answer")
        verbose_name_plural = _("user answers")
        ordering = ["-updated_at"]

    def __str__(self):
        return str(self.id)


class UserNameHistoricalModel(models.Model):
    """
    Abstract model for history models tracking Name.
    """
    name = CharField(max_length=1024, null=True, blank=True)

    class Meta:
        abstract = True


class VendorSurveyAnswer(BaseModel):
    question = models.ForeignKey(
        VendorSurveyQuestion, related_name="answers", on_delete=models.CASCADE, verbose_name=_("question")
    )
    user = models.ForeignKey(get_user_model(), blank=True, null=True, on_delete=models.CASCADE, verbose_name=_("user"))
    value = models.TextField(
        _("value"), help_text=_("The value of the answer given by the user."), null=True, blank=True
    )
    document = models.FileField(
        _("document"),
        help_text=_("The document of the answer given by the user."),
        max_length=4096,
        null=True,
        blank=True,
    )
    na_explain = models.TextField(
        _("na_explain"),
        help_text=_("NA explain of the answer given by the user."),
        null=True,
        blank=True,
        max_length=500,
    )
    answer_by_invited_user = models.BooleanField(default=False)
    user_answer = models.ForeignKey(VendorSurveyUserAnswer, on_delete=models.CASCADE, verbose_name=_("user answer"))
    history = HistoricalRecords(bases=[UserNameHistoricalModel])

    class Meta:
        verbose_name = _("answer")
        verbose_name_plural = _("answers")
        ordering = ["question__ordering"]

    def __str__(self):
        return f"{self.question}: {self.value}"

    @property
    def get_value(self):
        if self.question.type_field == TYPE_FIELD.rating:
            return create_star(active_star=int(self.value))
        elif self.question.type_field == TYPE_FIELD.url:
            return mark_safe(f'<a href="{self.value}" target="_blank">{self.value}</a>')
        elif (
            self.question.type_field == TYPE_FIELD.radio
            or self.question.type_field == TYPE_FIELD.select
            or self.question.type_field == TYPE_FIELD.multi_select
        ):
            return self.value.strip().replace("_", " ").capitalize()
        else:
            return self.value


class SurveyToken(models.Model):
    key = models.CharField(editable=False, unique=True, max_length=255)
    org = ForeignKey(Organization, on_delete=CASCADE)
    vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=CASCADE)
    user = models.ForeignKey(get_user_model(), blank=True, null=True, on_delete=models.CASCADE, verbose_name=_("user"))
    survey = models.ForeignKey(
        VendorSurvey, related_name="survey_token", on_delete=models.CASCADE, verbose_name=_("survey")
    )
    expiration_date = models.DateTimeField(editable=False, null=True, blank=True)

    def save(self, *args, **kwargs):
        today = timezone.now().date()
        self.expiration_date = today + timedelta(days=int(QUESTIONNAIRE_INVITATION_TTL))
        super(SurveyToken, self).save(*args, **kwargs)
