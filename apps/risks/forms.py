from customselectwidget.customselectwidget import CustomSelectWidget
from django.forms import (
    ModelChoiceField,
    ModelForm,
    TextInput,
    ValidationError,
)
from django.forms.widgets import DateTimeInput, Select, Textarea
from .models import Risk, get_risk_rating
from apps.vendor.models import Vendor
from django.utils import timezone


class RiskForm(ModelForm):
    """risk model form"""

    owner = ModelChoiceField(None, widget=Select(attrs={"class": "form-control"}), blank=True, required=False)

    def __init__(self, *args, **kwargs):
        model = kwargs.pop("model")
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = model.org.users.filter(is_invited=False).exclude(email__endswith="_gracen@gmail.com").order_by("last_name", "first_name", "email")
        self.fields["owner"].label_from_instance = self.owner_label_from_instance
        self.fields["owner"].label = "Owner"
        self.fields["owner"].initial = self.initial.get("owner_id") or self.initial.get("owner")
        self.fields["notes"].label = "Description"

    @staticmethod
    def owner_label_from_instance(obj):
        """return the label for an owner"""
        value = f"{obj.first_name} {obj.last_name}".strip()
        value = f"{value} - {obj.email}" if value else obj.email
        return value.strip()

    class Meta:
        model = Risk
        exclude = ["org"]
        widgets = {
            "title": TextInput(attrs={"class": "form-control"}),
            "mitigation": TextInput(attrs={"class": "form-control"}),
            "category": TextInput(attrs={"class": "form-control"}),
            "rating": TextInput(attrs={"class": "form-control", "id": "rating"}),
            "priority": Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "likelihood": Select(attrs={"class": "form-control", "id": "likelyhood"}),
            "impact": Select(attrs={"class": "form-control", "id": "severity"}),
            "notes": Textarea(
                attrs={
                    "class": "form-control resize-textarea",
                    "rows": "8",
                    "id": "notes-text",
                    "style": "height:190px; display:none",
                }
            ),
        }
