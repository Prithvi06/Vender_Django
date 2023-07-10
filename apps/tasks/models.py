from django.db import models
from django.utils import timezone
from organizations.models import Organization
from apps.authentication.models import User as AuthUser
from apps.incidents.models import Incident
from apps.risks.models import Risk
from apps.vendor.models import Contact, Contract, Vendor
from apps.administrator.models import OFACSDNResult, Location
from simple_history.models import HistoricalRecords
from datetime import datetime, timedelta
from django.utils.html import strip_tags
from apps.authentication.models import User
from pytz import timezone as time_zone


NOT_STARTED_TEXT = "Not Started"


PRIORITY_DISPLAYNAMES = {
    1: "Low",
    "LOW": "Low",
    2: "Medium",
    "MEDIUM": "Medium",
    3: "High",
    "HIGH": "High",
}

TASK_STATUS_DISPLAYNAMES = {
    1: NOT_STARTED_TEXT,
    "NOT_STARTED": NOT_STARTED_TEXT,
    2: "In Process",
    "IN_PROCESS": "In Process",
    3: "On Hold",
    "ON_HOLD": "On Hold",
    4: "Cancelled",
    "CANCELLED": "Cancelled",
    5: "Completed",
    "COMPLETED": "Completed",
}


class TaskPriority(models.IntegerChoices):
    """known priority"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


class TaskStatus(models.IntegerChoices):
    """TASK STATUS"""

    NOT_STARTED = 1
    IN_PROCESS = 2
    ON_HOLD = 3
    CANCELLED = 4
    COMPLETED = 5


class TaskCreatedBy(models.IntegerChoices):
    """Task created by"""

    USER = 0
    SYSTEM = 1


def get_task_circle(record):
    status_html = ""
    if record.status in [TaskStatus.IN_PROCESS, TaskStatus.NOT_STARTED]:
        due_date = record.due_date  # datetime(2023, 1, 30).date()
        created_at = record.created_at  # datetime(2023, 1, 15)
        if due_date:
            today = timezone.now().date()
            after_a_week = today + timedelta(days=7)
            create_diff = (due_date - created_at.date()).days
            today_diff = (due_date - today).days
            status_html = "<div class='task_status_circle'></div>"
            if due_date >= after_a_week:
                status_html = "<div class='task_status_circle'></div>"
            if ((create_diff > 7) and (today_diff < 7)) or ((create_diff <= 7) and (today_diff < (0.5 * create_diff))):
                status_html = "<div class='task_status_circle' style='background-color:#f8c533;'></div>"
            if due_date < today:
                status_html = "<div class='task_status_circle' style='background-color:#f2726f;'></div>"
        else:
            status_html = "<div class='task_status_circle'></div>"
    elif record.status == TaskStatus.COMPLETED:
        status_html = "<i class='material-icons task_status_icon'>check_circle</i>"
    elif record.status == TaskStatus.CANCELLED:
        status_html = "<i class='material-icons task_status_icon'>cancel</i>"
    elif record.status == TaskStatus.ON_HOLD:
        status_html = "<i class='material-icons task_status_icon'>front_hand</i>"
    return status_html


class Task(models.Model):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    title = models.CharField(max_length=1024)
    description = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    linked_resources = models.CharField(max_length=1024, null=True, blank=True)
    priority = models.IntegerField(choices=TaskPriority.choices, default=0)
    status = models.IntegerField(choices=TaskStatus.choices, default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    due_date = models.DateField(null=True, blank=True)
    closed_date = models.DateTimeField(null=True, blank=True)
    owner = models.ForeignKey(AuthUser, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.IntegerField(choices=TaskCreatedBy.choices, default=0, null=True)
    created_by_user = models.ForeignKey(
        AuthUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="createdBy"
    )
    contract = models.ForeignKey(Contract, on_delete=models.SET_NULL, null=True, blank=True)
    renewal_reminder_date = models.DateField(editable=False, null=True, blank=True)
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, null=True, blank=True)
    risk = models.ForeignKey(Risk, on_delete=models.SET_NULL, null=True, blank=True)
    incident = models.ForeignKey(Incident, on_delete=models.SET_NULL, null=True, blank=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, null=True, blank=True)
    ofac_result = models.ForeignKey(OFACSDNResult, on_delete=models.CASCADE, null=True, blank=True)
    parent_task = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()
    is_deleted = models.BooleanField(default=False)

    @property
    def get_notes(self):
        from apps.utility.VendorUtilities import get_linked_text

        if self.description:
            return get_linked_text(self.description)
        return ""

    def __str__(self):
        return self.title

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
                        if change.field in ["created_at", "closed_date"]:
                            pre_value = (
                                change.old.astimezone(time_zone("US/Pacific")).strftime("%m/%d/%y %I:%M %p")
                                if change.old
                                else ""
                            )
                            value = (
                                change.new.astimezone(time_zone("US/Pacific")).strftime("%m/%d/%y %I:%M %p")
                                if change.new
                                else ""
                            )
                        elif change.field == "due_date":
                            pre_value = change.old.strftime("%m/%d/%y") if change.old else ""
                            value = change.new.strftime("%m/%d/%y") if change.new else ""
                        elif change.field == "status":
                            pre_value = TASK_STATUS_DISPLAYNAMES[change.old]
                            value = TASK_STATUS_DISPLAYNAMES[change.new]
                        elif change.field == "linked_resources":
                            pre_value = change.old
                            value = change.new
                            if value:
                                value = value.split("#")
                                if len(value) > 1:
                                    value = value[2]
                                else:
                                    value = value
                            else:
                                value = ""
                            if pre_value:
                                pre_value = pre_value.split("#")
                                if len(pre_value) > 1:
                                    pre_value = pre_value[2]
                                else:
                                    pre_value = pre_value
                            else:
                                pre_value = ""
                        elif change.field == "priority":
                            pre_value = PRIORITY_DISPLAYNAMES[change.old]
                            value = PRIORITY_DISPLAYNAMES[change.new]
                        elif change.field in ["root_cause", "description"]:
                            pre_value = strip_tags(change.old).replace("&nbsp;", " ").strip() if change.old else ""
                            value = strip_tags(change.new).replace("&nbsp;", " ").strip() if change.new else ""
                        elif change.field == "owner":
                            value = ""
                            pre_value = ""
                            if change.new:
                                owner_object = User.objects.filter(pk=change.new).first()
                                if owner_object:
                                    value = f"{owner_object.first_name} {owner_object.last_name}"
                            if change.old:
                                owner_object = User.objects.filter(pk=change.old).first()
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

    @property
    def get_status_task(self):
        return get_task_circle(self)


class TaskAuditHistory(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    audit_history = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
