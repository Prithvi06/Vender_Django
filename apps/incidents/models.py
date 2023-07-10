from django.db import models
from organizations.models import Organization
from simple_history.models import HistoricalRecords
from datetime import datetime
from django.utils.html import strip_tags
from pytz import timezone as time_zone

# Create your models here.


SEVERITY_DISPLAYNAMES = {
    1: "Low",
    "LOW": "Low",
    2: "Medium",
    "MEDIUM": "Medium",
    3: "High",
    "HIGH": "High",
    4: "Critical",
    "CRITICAL": "Critical",
}

INCIDENT_STATUS_DISPLAYNAMES = {
    1: "Reported",
    "REPORTED": "Reported",
    2: "Active",
    "ACTIVE": "Active",
    3: "Extended Remediation",
    "EXTENDED_REMEDIATION": "Extended Remediation",
    4: "Closed",
    "CLOSED": "Closed",
    5: "Not An Incident",
    "NOT_AN_INCIDENT": "Not An Incident",
}


class Severity(models.IntegerChoices):
    """known severity"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class IncidentStatus(models.IntegerChoices):
    """known incident status"""

    REPORTED = 1
    ACTIVE = 2
    EXTENDED_REMEDIATION = 3
    CLOSED = 4
    NOT_AN_INCIDENT = 5


class Incident(models.Model):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    title = models.CharField(max_length=1024)
    description = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    root_cause = models.TextField(null=True, blank=True)
    affected_resources = models.CharField(max_length=1024, null=True, blank=True)
    severity = models.IntegerField(choices=Severity.choices, default=0)
    status = models.IntegerField(choices=IncidentStatus.choices, default=0)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    history = HistoricalRecords()

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
                        if change.field == "end_date" or change.field == "start_date":
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
                        elif change.field == "status":
                            pre_value = INCIDENT_STATUS_DISPLAYNAMES[change.old]
                            value = INCIDENT_STATUS_DISPLAYNAMES[change.new]
                        elif change.field == "severity":
                            pre_value = SEVERITY_DISPLAYNAMES[change.old]
                            value = SEVERITY_DISPLAYNAMES[change.new]
                        elif change.field in ["root_cause", "description"]:
                            pre_value = strip_tags(change.old).replace("&nbsp;", " ").strip()
                            value = strip_tags(change.new).replace("&nbsp;", " ").strip()
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
    def get_description(self):
        from apps.utility.VendorUtilities import get_linked_text

        if self.description:
            return get_linked_text(self.description)
        return ""

    @property
    def get_cause(self):
        from apps.utility.VendorUtilities import get_linked_text

        if self.root_cause:
            return get_linked_text(self.root_cause)
        return ""
