from customselectwidget.customselectwidget import CustomSelectWidget
from django.forms import (
    ModelChoiceField,
    ModelForm,
    TextInput,
    ValidationError,
)
from django.forms.widgets import DateTimeInput, Select, Textarea, DateInput
from .models import Task
from apps.vendor.models import Vendor, Contact, Contract
from apps.risks.models import Risk
from apps.incidents.models import Incident
from django.utils import timezone


PRIORITY_CHOICES = (
    (1, "Low"),
    (2, "Medium"),
    (3, "High"),
    (4, "Critical"),
)


TASK_STATUS_CHOICES = (
    (1, "Reported"),
    (2, "Active"),
    (3, "Extended Remediation"),
    (4, "Closed"),
    (5, "Non An Incident"),
)


class TaskForm(ModelForm):
    """task model form"""

    owner = ModelChoiceField(None, widget=Select(attrs={"class": "form-control"}), blank=True, required=False)

    def __init__(self, *args, **kwargs):
        model = kwargs.pop("model")
        super().__init__(*args, **kwargs)
        self.fields["linked_resources"].label = "Linked Resource"
        self.fields["due_date"].label = "Due Date"
        self.fields["closed_date"].label = "Completed Date / Time"
        self.fields["owner"].queryset = (
            model.org.users.filter(is_invited=False)
            .exclude(email__endswith="_gracen@gmail.com")
            .order_by("last_name", "first_name", "email")
        )
        self.fields["owner"].label_from_instance = self.owner_label_from_instance
        self.fields["owner"].label = "Owner"
        self.fields["owner"].initial = self.initial.get("owner_id") or self.initial.get("owner")

    @staticmethod
    def owner_label_from_instance(obj):
        """return the label for an owner"""
        value = f"{obj.first_name} {obj.last_name}".strip()
        value = f"{value} - {obj.email}" if value else obj.email
        return value.strip()

    class Meta:
        model = Task
        exclude = [
            "org",
            "created_by",
            "created_by_user",
            "contract",
            "contact",
            "risk",
            "incident",
            "vendor",
            "ofac_result",
            "parent_task",
            "notes",
        ]
        widgets = {
            "title": TextInput(attrs={"class": "form-control"}),
            "priority": Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "linked_resources": TextInput(
                attrs={"class": "form-control", "id": "form_linked_resource", "style": "display: none;"}
            ),
            "due_date": DateInput(attrs={"class": "form-control", "type": "date"}),
            "closed_date": DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "status": Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "description": Textarea(
                attrs={
                    "class": "form-control resize-textarea",
                    "rows": "4",
                    "style": "height: 120px; display:none;",
                    "id": "notes-text",
                }
            ),
            "notes": Textarea(
                attrs={
                    "class": "form-control resize-textarea",
                    "rows": "4",
                    "style": "height: 120px;",
                }
            ),
        }
