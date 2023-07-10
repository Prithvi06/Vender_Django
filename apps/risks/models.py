from django.db import models
from organizations.models import Organization
from apps.authentication.models import User as AuthUser
from django.utils import timezone
from simple_history.models import HistoricalRecords
from datetime import datetime
from django.utils.html import strip_tags
from apps.authentication.models import User
from pytz import timezone as time_zone

# Create your models here.


PRIORITY_DISPLAYNAMES = {
    1: "Low",
    "LOW": "Low",
    2: "Medium",
    "MEDIUM": "Medium",
    3: "High",
    "HIGH": "High",
    4: "Critical",
    "CRITICAL": "Critical",
}


class RiskPriority(models.IntegerChoices):
    """known priority"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


PICKLIST_CHOICES = (
    (1, 1),
    (2, 2),
    (3, 3),
    (4, 4),
    (5, 5),
)


def get_risk_rating(rating):
    if rating <= 5:
        return "Low"
    elif rating >= 6 and rating <= 11:
        return "Medium"
    else:
        return "High"


class Risk(models.Model):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    title = models.CharField(max_length=1024)
    mitigation = models.CharField(max_length=1024, null=True, blank=True)
    impact = models.IntegerField(default=1, choices=PICKLIST_CHOICES)
    priority = models.IntegerField(choices=RiskPriority.choices, default=0)
    likelihood = models.IntegerField(default=1, choices=PICKLIST_CHOICES)
    rating = models.IntegerField(default=1)
    category = models.CharField(max_length=1024, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    notes = models.TextField(null=True, blank=True)
    owner = models.ForeignKey(AuthUser, on_delete=models.SET_NULL, null=True, blank=True)
    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        self.rating = int(self.impact) * int(self.likelihood)
        super(Risk, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def get_rating(self):
        return get_risk_rating(self.rating)

    @property
    def get_notes(self):
        from apps.utility.VendorUtilities import get_linked_text

        if self.notes:
            return get_linked_text(self.notes)
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
                        author = (
                            f"{data.next_record.history_user.first_name} {data.next_record.history_user.last_name}"
                        ).capitalize()
                    history_str = (
                        history_str
                        + f"<h6 class='mb-0 mt-2' style='color:black;'>{str(data.next_record.history_date.astimezone(time_zone('US/Pacific')).strftime('%m/%d/%y %I:%M %p'))} - {author}</h6>"
                    )
                    for change in delta.changes:
                        if change.field == "priority":
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


class RiskAuditHistory(models.Model):
    risk = models.ForeignKey(Risk, on_delete=models.CASCADE)
    audit_history = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def get_history(self):
        from apps.utility.VendorUtilities import get_linked_text

        if self.audit_history:
            return get_linked_text(self.audit_history)
        return ""
