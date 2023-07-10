from customselectwidget.customselectwidget import CustomSelectWidget
from django.forms import (
    ModelForm,
    TextInput,
    ModelChoiceField
)
from django.forms.widgets import DateInput, Select
from .models import System
from apps.vendor.models import Vendor

def get_system_type(org):
    """get all unique system types"""
    data = System.objects.filter(org=org).values_list("system_type", flat=True).filter(system_type__isnull=False)
    unique = set(data)
    result = list(unique)
    result.sort()
    return result


class SystemForm(ModelForm):
    """System model form"""

    def __init__(self, *args, **kwargs):
        model = kwargs.pop("model")
        super().__init__(*args, **kwargs)
        self.fields["name"].label = "Name"
        self.fields["asset_id"].label = "Asset Number / ID"
        self.fields["account_id"].label = "Account / License ID"
        self.fields["vendor"].label = "Vendor"
        self.fields["inservice_date"].label = "Inservice Date"
        self.fields["retired_date"].label = "Retired Date"
        self.fields["system_type"].label = "System Type"
        self.fields["system_type"].widget = CustomSelectWidget(
            data_list=kwargs.pop("system_type") if "system_type" in kwargs else get_system_type(model.org) or [],
            name="system_type",
            attrs={"class": "form-control"},
        )
        self.fields["hosting"].label = "Hosting"
        self.fields["hosting"].initial = self.initial.get("hosting")


    class Meta:
        model = System
        exclude = ["org"]
        widgets = {
            "name": TextInput(attrs={"class": "form-control"}),
            "asset_id": TextInput(attrs={"class": "form-control", "id": "asset_id"}),
            "account_id": TextInput(attrs={"class": "form-control", "id": "account_id"}),
            "vendor": TextInput(attrs={"class": "form-control", "id": "vendor", "style": "display: none"}),
            "inservice_date": DateInput(attrs={"type": "date", "class": "form-control", "id": "inservice_date"}),
            "retired_date": DateInput(attrs={"type": "date", "class": "form-control", "id": "retired_date"}),
        }