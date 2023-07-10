from customselectwidget.customselectwidget import CustomSelectWidget
from django.forms import (
    ModelForm,
    TextInput,
    ModelChoiceField
)
from django.forms.widgets import DateInput, Select
from .models import Equipment
from apps.vendor.models import Vendor


def get_equipment_type(org):
    """get all unique equipment types"""
    data = Equipment.objects.filter(org=org).values_list("equipment_type", flat=True).filter(equipment_type__isnull=False)
    unique = set(data)
    result = list(unique)
    result.sort()
    return result


class EquipmentForm(ModelForm):
    """Equipment model form"""

    def __init__(self, *args, **kwargs):
        model = kwargs.pop("model")
        super().__init__(*args, **kwargs)
        self.fields["name"].label = "Name"
        self.fields["asset_id"].label = "Asset Number / ID"
        self.fields["serial_num"].label = "Serial Number"
        self.fields["vendor"].label = "Vendor"
        self.fields["inservice_date"].label = "Inservice Date"
        self.fields["retired_date"].label = "Retired Date"
        self.fields["equipment_type"].label = "Equipment Type"
        self.fields["equipment_type"].widget = CustomSelectWidget(
            data_list=kwargs.pop("equipment_type") if "equipment_type" in kwargs else get_equipment_type(model.org) or [],
            name="equipment_type",
            attrs={"class": "form-control"},
        )


    class Meta:
        model = Equipment
        exclude = ["org"]
        widgets = {
            "name": TextInput(attrs={"class": "form-control"}),
            "asset_id": TextInput(attrs={"class": "form-control", "id": "asset_id"}),
            "serial_num": TextInput(attrs={"class": "form-control", "id": "serial_num"}),
            "vendor": TextInput(attrs={"class": "form-control", "id": "vendor", "style": "display: none"}),
            "inservice_date": DateInput(attrs={"type": "date", "class": "form-control", "id": "inservice_date"}),
            "retired_date": DateInput(attrs={"type": "date", "class": "form-control", "id": "retired_date"}),

        }