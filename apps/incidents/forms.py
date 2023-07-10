from customselectwidget.customselectwidget import CustomSelectWidget
from django.forms import (
    ModelChoiceField,
    ModelForm,
    TextInput,
    ValidationError,
)
from django.forms.widgets import DateTimeInput, Select, Textarea
from .models import Incident
from apps.vendor.models import Vendor


SEVERITY_CHOICES = (
    (1, "Low"),
    (2, "Medium"),
    (3, "High"),
    (4, "Critical"),
)


INCIDENT_STATUS_CHOICES = (
    (1, "Reported"),
    (2, "Active"),
    (3, "Extended Remediation"),
    (4, "Closed"),
    (5, "Non An Incident"),
)


def get_vendors(org):
    """get all vendors"""
    data = Vendor.objects.filter(org=org)
    unique = set(data)
    result = list(unique)
    return result


class IncidentForm(ModelForm):
    """incident model form"""

    def __init__(self, *args, **kwargs):
        model = kwargs.pop("model")
        super().__init__(*args, **kwargs)
        self.fields["affected_resources"].label = "Linked Resource(s)"
        self.fields["start_date"].label = "Start Date / Time"
        self.fields["end_date"].label = "End Date / Time"

    class Meta:
        model = Incident
        exclude = ["org", "notes"]
        widgets = {
            "title": TextInput(attrs={"class": "form-control"}),
            "severity": Select(
                attrs={
                    "class": "form-control",
                },
                choices=SEVERITY_CHOICES,
            ),
            "start_date": DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "end_date": DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "status": Select(
                attrs={
                    "class": "form-control",
                },
                choices=INCIDENT_STATUS_CHOICES,
            ),
            "affected_resources": TextInput(
                attrs={"class": "form-control", "id": "linked_resource", "style": "display:none"}
            ),
            "description": Textarea(
                attrs={
                    "class": "form-control resize-textarea",
                    "rows": "5",
                    "style": "height:124px;",
                    "id": "description-text",
                    "style": "height:90px; display: none;",
                }
            ),
            "root_cause": Textarea(
                attrs={
                    "class": "form-control resize-textarea",
                    "rows": "5",
                    "style": "height:124px;",
                    "id": "cause-text",
                    "style": "height:90px; display: none;",
                }
            ),
        }
