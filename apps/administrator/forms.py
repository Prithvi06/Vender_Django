from customselectwidget.customselectwidget import CustomSelectWidget
from django.forms import (
    ModelForm,
    TextInput,
    ValidationError,
)
from django.forms.widgets import DateInput, FileInput, NumberInput, Select, Textarea
from phonenumber_field.formfields import PhoneNumberField
from .models import Location

def get_location_type(org):
    """get all unique vendor residual risk"""
    data = Location.objects.filter(org=org).values_list("location_type", flat=True).filter(location_type__isnull=False)
    unique = set(data)
    result = list(unique)
    # result.sort()
    return result

class LocationForm(ModelForm):
    """vendor model form"""

    primary_phone = PhoneNumberField(region="US", widget=TextInput(attrs={"class": "form-control"}))
    
    def __init__(self, *args, **kwargs):
        model = kwargs.pop("model")
        super().__init__(*args, **kwargs)
        self.fields["name"].label = "Name"
        self.fields["line_1"].label = "Address Line 1"
        self.fields["line_2"].label = "Address Line 2"
        self.fields["city"].label = "city"
        self.fields["state"].label = "State"
        self.fields["zip_code"].label = "Zip Code"
        self.fields["location_type"].label = "Location Type"
        self.fields["location_code"].label = "Location Code"
        self.fields["landlord"].label = "Landlord"
        self.fields["primary_phone"].label = "Primary Phone"
        self.fields["location_type"].widget = CustomSelectWidget(
            data_list=kwargs.pop("location_type") if "location_type" in kwargs else get_location_type(model.org) or [],
            name="location_type",
            attrs={"class": "form-control"},
        )


    def clean_name(self):
        """ensure name is not alread in use with same organization"""
        value = self.cleaned_data.get("name")

        # ensure the value is unique at this point
        if value:
            conflict = (
                Location.objects.exclude(pk=self.instance.id).filter(org=self.instance.org, name=value).first()
            )
            if conflict:
                raise ValidationError(f"{conflict.name} Name is already in use in current organization.")
        return value

    def clean_location_code(self):
        """ensure name is not alread in use with same organization"""
        value = self.cleaned_data.get("location_code")

        # ensure the value is unique at this point
        if value:
            conflict = (
                Location.objects.exclude(pk=self.instance.id).filter(org=self.instance.org, location_code=value).first()
            )
            if conflict:
                raise ValidationError(f"{conflict.location_code} is already in use in current organization")
        return value


    class Meta:
        model = Location
        exclude = ["org", "updated_at"]
        widgets = {
            "name": TextInput(attrs={"class": "form-control"}),
            "line_1": TextInput(attrs={"class": "form-control", "id": "address_line1", "placeholder": ""}),
            "line_2": TextInput(attrs={"class": "form-control", "id": "address_line2", "placeholder": ""}),
            "city": TextInput(attrs={"class": "form-control", "id": "locality"}),
            "state": TextInput(attrs={"class": "form-control", "id": "administrative_area_level_1"}),
            "zip_code": TextInput(attrs={"class": "form-control", "id": "postal_code"}),
            "location_code": TextInput(attrs={"class": "form-control", "id": "location_code"}),
            "landlord": TextInput(attrs={"class": "form-control", "id": "landlord", "style": "display:none"}),
        }
