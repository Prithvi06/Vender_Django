from datetime import date

from django.db import models
from organizations.models import Organization
from phonenumber_field.modelfields import PhoneNumberField
from apps.authentication.models import User as AuthUser
from apps.vendor.models import Contact, Vendor
from django.utils.timezone import localtime, now
from django.utils.functional import lazy
import datetime

ENT_NUM_HELP_TEXT = "unique record/listing identifier"


class Category(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=1000, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)


class OrganizationSetting(models.Model):
    business_process_choices = (
        ("LEVEL_1", "LEVEL_1"),
        ("LEVEL_2", "LEVEL_2"),
        ("LEVEL_3", "LEVEL_3"),
    )
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    business_process_level = models.CharField(max_length=255, null=True, blank=True, choices=business_process_choices)


class BusinessUnit(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=1000, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)


class Department(models.Model):
    unit = models.ForeignKey(BusinessUnit, on_delete=models.CASCADE, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=1000, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)


class Process(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=1000, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)


class BusinessProcess(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    unit = models.ForeignKey(BusinessUnit, on_delete=models.CASCADE, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)
    process = models.ForeignKey(Process, on_delete=models.CASCADE, null=True, blank=True)


class Location(models.Model):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=1024)
    line_1 = models.CharField(max_length=1024, null=True, blank=True)
    line_2 = models.CharField(max_length=1024, null=True, blank=True)
    city = models.CharField(max_length=1024, null=True, blank=True)
    state = models.CharField(max_length=2, null=True, blank=True)
    zip_code = models.CharField(max_length=9, null=True, blank=True)
    location_type = models.CharField(max_length=1024, null=True, blank=True)
    location_code = models.CharField(max_length=1024)
    landlord = models.CharField(max_length=1024, null=True, blank=True)
    primary_phone = PhoneNumberField()
    ignore_sdn = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateField(auto_now=True, blank=True, null=True)

    def __str__(self):
        return self.name


name_choices = (("OFAC", "OFAC"), ("SENDGRID_EMAIL", "SENDGRID_EMAIL"), ("OTHER", "OTHER"))


class TestEmailService(models.Model):
    user = models.ForeignKey(AuthUser, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        from apps.vendor.tasks import send_contract_status

        send_contract_status.delay(self.user.id)
        super(TestEmailService, self).save(*args, **kwargs)


class ScheduledJobLogger(models.Model):
    api_url = models.CharField(max_length=1000, null=True, blank=True)
    email = models.CharField(max_length=1000, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    response_code = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    job_type = models.CharField(max_length=30, null=True, blank=True, choices=name_choices)


class OFACBase(models.Model):
    id = models.CharField(max_length=17, primary_key=True)
    created_at = models.DateField(default=date(1, 1, 1))
    ent_num = models.IntegerField(default=0)

    @staticmethod
    def get_surrogate_key(created_at: date, natural_key: int):
        date_string = created_at.strftime("%Y%m%d")
        natural_string = str(natural_key).rjust(8, "0")
        return f"{date_string}-{natural_string}"

    class Meta:
        abstract = True


class OFACSpeciallyDesignatedNational(OFACBase):
    """
    Office Of Foreign Assets Control (OFAC) Specially Designated National (SDN)
    See https://home.treasury.gov/policy-issues/financial-sanctions/specially-designated-nationals-list-data-formats-data-schemas for usage and purpose.
    See https://home.treasury.gov/system/files/126/dat_spec.txt for CSV format specification.
    """

    name = models.CharField(max_length=350, null=True, blank=True, help_text="name of SDN")
    sdn_type = models.CharField(max_length=12, null=True, blank=True, help_text="type of SDN")
    program = models.CharField(max_length=200, null=True, blank=True, help_text="sanctions program name")
    title = models.CharField(max_length=200, null=True, blank=True, help_text="title of an individual")
    call_sign = models.CharField(max_length=8, null=True, blank=True, help_text="vessel call sign")
    vess_type = models.CharField(max_length=25, null=True, blank=True, help_text="vessel type")
    tonnage = models.CharField(max_length=14, null=True, blank=True, help_text="vessel tonnage")
    grt = models.CharField(max_length=8, null=True, blank=True, help_text="gross registered tonnage")
    vess_flag = models.CharField(max_length=40, null=True, blank=True, help_text="vessel flag")
    vess_owner = models.CharField(max_length=150, null=True, blank=True, help_text="vessel owner")
    remarks = models.TextField(null=True, blank=True, help_text="remarks on SDN")

    def __str__(self):
        return self.id

    class Meta:
        verbose_name = "OFAC SDN"
        verbose_name_plural = "OFAC SDNs"


class OFACSpeciallyDesignatedNationalAddress(OFACBase):
    """
    Office Of Foreign Assets Control (OFAC) Specially Designated National (SDN)
    See https://home.treasury.gov/policy-issues/financial-sanctions/specially-designated-nationals-list-data-formats-data-schemas for usage and purpose.
    See https://home.treasury.gov/system/files/126/dat_spec.txt for CSV format specification.
    """

    sdn = models.ForeignKey(OFACSpeciallyDesignatedNational, on_delete=models.CASCADE)
    add_num = models.IntegerField(help_text=ENT_NUM_HELP_TEXT)
    address = models.CharField(max_length=750, null=True, blank=True, help_text="street address of SDN")
    address_line_2 = models.CharField(
        max_length=116, null=True, blank=True, help_text="city, state/province, zip/postal code"
    )
    country = models.CharField(max_length=250, null=True, blank=True, help_text="country of address")
    add_remarks = models.CharField(max_length=200, null=True, blank=True, help_text="remarks on address")

    class Meta:
        verbose_name = "OFAC Address"
        verbose_name_plural = "OFAC Addresses"


class OFACSpeciallyDesignatedNationalAlternate(OFACBase):
    """
    Office Of Foreign Assets Control (OFAC) Specially Designated National (SDN)
    See https://home.treasury.gov/policy-issues/financial-sanctions/specially-designated-nationals-list-data-formats-data-schemas for usage and purpose.
    See https://home.treasury.gov/system/files/126/dat_spec.txt for CSV format specification.
    """

    sdn = models.ForeignKey(OFACSpeciallyDesignatedNational, on_delete=models.CASCADE)
    alt_num = models.IntegerField(help_text=ENT_NUM_HELP_TEXT)
    alt_type = models.CharField(
        max_length=8, null=True, blank=True, help_text="type of alternate identity (aka, fka, nka)"
    )
    alt_name = models.CharField(max_length=350, null=True, blank=True, help_text="alternate identity name")
    alt_remarks = models.CharField(max_length=200, null=True, blank=True, help_text="remarks on alternate identity")

    class Meta:
        verbose_name = "OFAC Alias"
        verbose_name_plural = "OFAC Aliases"


class OFACSDNResult(models.Model):
    hash_code = models.CharField(max_length=255, unique=True)
    total_sdn = models.PositiveBigIntegerField(default=1)
    total_address = models.PositiveBigIntegerField(default=0)
    total_alias = models.PositiveBigIntegerField(default=0)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, null=True, blank=True)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, null=True, blank=True)
    result = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "OFAC SDN Result"
        verbose_name_plural = "OFAC SDN Results"


class BulkImport(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    file = models.FileField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        pass


sdn_services = (
    ("DOWNLOAD_OFAC_FILES", "DOWNLOAD_OFAC_FILES"),
    ("OFAC_SCAN_ON_CONTACT", "OFAC_SCAN_ON_CONTACT"),
    ("CLEAR_OFAC_LIST", "CLEAR_OFAC_LIST"),
)


class SiteFeatures(models.Model):
    enable = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.enable:
            AuthUser.objects.all().update(feature_permission=True)
        else:
            AuthUser.objects.all().update(feature_permission=False)
        super(SiteFeatures, self).save(*args, **kwargs)
