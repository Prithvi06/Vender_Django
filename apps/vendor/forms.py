""" vendor forms module """
from customselectwidget.customselectwidget import CustomSelectWidget
from django.forms import (
    EmailInput,
    ModelChoiceField,
    ModelForm,
    TextInput,
    ValidationError,
)
from django.forms.widgets import DateInput, FileInput, NumberInput, Select, Textarea
from phonenumber_field.formfields import PhoneNumberField

from .models import Contact, Contract, Document, Phone, Vendor, ContractStatus
from apps.administrator.models import BusinessUnit, Department, Process, OrganizationSetting

TRUE_FALSE_CHOICES = (
    (False, "No"),
    (True, "Yes"),
)

CONTRACT_RENEWAL_PAD_CHOICES = (
    (0, "None"),
    (15, "15 days"),
    (30, "30 days"),
    (45, "45 days"),
    (60, "60 days"),
)


RISK_GRADE_CHOICES = ((0, "None"), (1, "Low"), (2, "Medium"), (3, "High"))


def get_vendor_categories(org):
    """get all unique categories across all vendors"""
    data = Vendor.objects.filter(org=org).values_list("category", flat=True).filter(category__isnull=False)
    unique = set(data)
    result = list(unique)
    result.sort()
    return result


# def get_vendor_process(org):
#     level_obj = OrganizationSetting.objects.filter(organization_id=org)
#     units = BusinessUnit.objects.filter(organization_id=org, is_deleted=False)
#     departments = Department.objects.filter(organization_id=org, is_deleted=False)
#     processes = Process.objects.filter(organization_id=org, is_deleted=False)
#     data = []
#     if level_obj:
#         if units:
#             for unit in units:
#                 for department in departments.filter(unit=unit):
#                     for process in processes.filter(department=department):
#                         data.append(f"{unit.name} - {department.name} - {process.name}")
#     else:
#         for unit in units:
#             for department in departments.filter(unit=unit):
#                 for process in processes.filter(department=department):
#                     data.append(f"{unit.name} - {department.name} - {process.name}")

#     unique = set(data)
#     result = list(unique)
#     return result


class VendorForm(ModelForm):
    """vendor model form"""

    owner = ModelChoiceField(
        None,
        widget=Select(attrs={"class": "form-control"}),
        blank=True,
        required=False,
    )

    def __init__(self, *args, **kwargs):
        model = kwargs.pop("model")
        super().__init__(*args, **kwargs)
        self.fields["legal_name"].label = "Legal Name"
        self.fields["legal_structure"].label = "Legal Structure"
        self.fields["inherent_risk"].label = "Inherent Risk"
        self.fields["residual_risk"].label = "Residual Risk"
        self.fields["critical"].label = "Is Critical?"
        self.fields["is_offshore"].label = "Is Offshore?"
        self.fields["org_business_process"].label = "Business Process"
        self.fields["vendor_optional_id"].label = "Third Party ID"
        self.fields["category"].widget = CustomSelectWidget(
            data_list=kwargs.pop("categories") if "categories" in kwargs else get_vendor_categories(model.org) or [],
            name="type-list",
            attrs={"class": "form-control"},
        )
        # org_business_process = get_vendor_process(model.org)
        # org_business_process_list = []
        # org_business_process_list.append(("", ""))
        # for org_p in org_business_process:
        #     org_business_process_list.append((org_p, org_p))
        # self.fields["org_business_process"].widget = Select(
        #     attrs={"class": "form-control", "id": "select-unit"},
        #     choices=org_business_process_list,
        # )
        self.fields["owner"].queryset = model.org.users.order_by("last_name", "first_name", "email")
        self.fields["owner"].label_from_instance = self.owner_label_from_instance
        self.fields["owner"].label = "Third Party Relationship Owner"
        self.fields["owner"].initial = self.initial.get("owner_id") or self.initial.get("owner")
        self.fields["tax_id_number"].label = "Tax ID Number"
        self.fields["risk_description"].label = "Risk Description(s)"
        self.fields["risk_type"].label = "Risk Type(s)"

    def clean_tax_id_number(self):
        """ensure tax_id_number is not alread in use"""
        value = self.cleaned_data.get("tax_id_number")

        # ensure the value is unique at this point
        if value:
            conflict = (
                Vendor.objects.exclude(pk=self.instance.id).filter(org=self.instance.org, tax_id_number=value).first()
            )
            if conflict:
                raise ValidationError(f"Tax ID Number is already in use by vendor {conflict.name}.")

        return value

    # def clean_org_business_process(self):
    #     value = self.cleaned_data.get("org_business_process")
    #     if value:
    #         level_obj = OrganizationSetting.objects.filter(organization=self.instance.org)
    #         validated_value = value.split("-")
    #         if level_obj:
    #             if len(validated_value) != 3:
    #                 raise ValidationError("Expected format: Unit-Department-Process")
    #     return value

    @staticmethod
    def owner_label_from_instance(obj):
        """return the label for an owner"""
        value = f"{obj.first_name} {obj.last_name}".strip()
        value = f"{value} ({obj.email})" if value else obj.email
        return value.strip()

    class Meta:
        model = Vendor
        exclude = ["org", "ignore_sdn"]
        widgets = {
            "name": TextInput(attrs={"class": "form-control"}),
            "legal_name": TextInput(attrs={"class": "form-control"}),
            "is_offshore": Select(
                attrs={"class": "form-control"},
                choices=TRUE_FALSE_CHOICES,
            ),
            "critical": Select(
                attrs={"class": "form-control"},
                choices=TRUE_FALSE_CHOICES,
            ),
            "legal_structure": Select(attrs={"class": "form-control"}),
            "risk_type": TextInput(
                attrs={"class": "form-control", "id": "risk_type", "style": "display: none;"},
            ),
            "inherent_risk": Select(attrs={"class": "form-control"}),
            "residual_risk": Select(
                attrs={"class": "form-control"},
                choices=RISK_GRADE_CHOICES,
            ),
            "status": Select(
                attrs={"class": "form-control"},
                choices=RISK_GRADE_CHOICES,
            ),
            "owner": TextInput(attrs={"class": "form-control"}),
            "tax_id_number": TextInput(
                attrs={
                    "class": "form-control",
                }
            ),
            "twitter": TextInput(
                attrs={"class": "form-control", "onkeyup": "activeBrowse('twitter')", "id": "twitter_input"}
            ),
            "linkedin": TextInput(
                attrs={"class": "form-control", "onkeyup": "activeBrowse('linkedin')", "id": "linkedin_input"}
            ),
            "website": TextInput(
                attrs={"class": "form-control", "onkeyup": "activeBrowse('website')", "id": "website_input"}
            ),
            "facebook": TextInput(
                attrs={"class": "form-control", "onkeyup": "activeBrowse('facebook')", "id": "facebook_input"}
            ),
            "stock_symbol": TextInput(
                attrs={"class": "form-control", "onkeyup": "activeBrowse('stock_symbol')", "id": "stock_symbol_input"}
            ),
            "notes": Textarea(
                attrs={
                    "class": "form-control",
                    "rows": "10",
                    "id": "notes-text",
                    "style": "height:219px; display: none; border: 1px solid #d2d2d2; padding: 10px; resize: vertical;",
                }
            ),
            "risk_description": Textarea(
                attrs={
                    "class": "form-control resize-textarea",
                    "rows": "10",
                    "style": "height: 265px; display: none;",
                    "id": "description-text",
                }
            ),
            "vendor_optional_id": TextInput(attrs={"class": "form-control"}),
            "rank": Select(attrs={"class": "form-control"}),
        }


class ContactForm(ModelForm):
    """contact model form"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].label = "Type"
        self.fields["line_1"].label = "Address Line 1"
        self.fields["line_2"].label = "Address Line 2"

    class Meta:
        model = Contact
        exclude = ["vendor", "ignore_sdn", "notes"]
        widgets = {
            "first_name": TextInput(attrs={"class": "form-control"}),
            "last_name": TextInput(attrs={"class": "form-control"}),
            "email": EmailInput(attrs={"class": "form-control"}),
            "line_1": TextInput(attrs={"class": "form-control", "id": "address_line1", "placeholder": ""}),
            "line_2": TextInput(attrs={"class": "form-control", "id": "sublocality_level_1"}),
            "city": TextInput(attrs={"class": "form-control", "id": "locality"}),
            "state": TextInput(attrs={"class": "form-control", "id": "administrative_area_level_1"}),
            "zip_code": TextInput(attrs={"class": "form-control", "id": "postal_code"}),
            "role": Select(attrs={"class": "form-control"}),
        }


class PhoneForm(ModelForm):
    """phone model form"""

    number = PhoneNumberField(region="US", widget=TextInput(attrs={"class": "form-control"}))

    class Meta:
        model = Phone
        exclude = ["contact"]
        widgets = {
            "type": Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "is_preferred": Select(attrs={"class": "form-control"}, choices=TRUE_FALSE_CHOICES),
        }


class ContractForm(ModelForm):
    """contract model form"""

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.fields["is_auto_renew"].label = "Auto Renews at Expiration"
        self.fields["has_minimum_fees"].label = "Has Minimum Fees"
        self.fields["contract_optional_id"].label = "Contract ID"

    class Meta:
        model = Contract
        exclude = ["vendor", "parent_contract", "superseded_by"]
        widgets = {
            "title": TextInput(attrs={"class": "form-control"}),
            "effective_date": DateInput(attrs={"class": "form-control", "type": "date"}),
            "next_expiration": DateInput(attrs={"class": "form-control", "type": "date"}),
            "renewal_period_days": NumberInput(
                attrs={"class": "form-control", "style": "height: calc(2.4375rem + 2px);"}
            ),
            "renewal_pad": Select(attrs={"class": "form-control"}, choices=CONTRACT_RENEWAL_PAD_CHOICES),
            "terms": Textarea(
                attrs={
                    "class": "form-control resize-textarea",
                    "rows": "10",
                    "id": "notes-text",
                    "style": "height: 350px; display:none;",
                }
            ),
            "status": Select(
                attrs={"class": "form-control"},
                choices=ContractStatus.choices,
            ),
            "is_auto_renew": Select(attrs={"class": "form-control"}, choices=TRUE_FALSE_CHOICES),
            "has_minimum_fees": Select(attrs={"class": "form-control"}, choices=TRUE_FALSE_CHOICES),
            "contract_optional_id": TextInput(attrs={"class": "form-control"}),
        }


class DocumentForm(ModelForm):
    """document model form"""

    contract = ModelChoiceField(
        None, widget=Select(attrs={"class": "form-control", "id": "id_contract"}), blank=True, required=False
    )

    def __init__(self, *args, **kwargs):
        super(DocumentForm, self).__init__(*args, **kwargs)
        self.fields["contract"].queryset = Contract.objects.all()
        self.fields["contract"].label = "Link"
        self.fields["contract"].initial = self.initial.get("contract_id")

    class Meta:
        model = Document
        exclude = ["name", "vendor"]
        widgets = {
            "description": TextInput(attrs={"class": "form-control"}),
            "path": FileInput(attrs={"class": "form-control", "title": "Document", "style": "display: none;"}),
        }
