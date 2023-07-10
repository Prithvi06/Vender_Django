from django.db import models
from organizations.models import Organization
from apps.vendor.models import Vendor

# Create your models here.

class HostingType(models.IntegerChoices):
    """known hosting types"""

    SAAS = 1
    VENDOR_HOSTED = 2
    CLOUD = 3
    DATA_CENTER = 4
    ONPREM = 5


class System(models.Model):

    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=1024)
    system_type = models.CharField(max_length=1024)
    asset_id = models.CharField(max_length=1024)
    account_id = models.CharField(max_length=1024, null=True, blank=True)
    vendor = models.CharField(max_length=1024, null=True, blank=True)
    inservice_date = models.DateField(max_length=1024, null=True, blank=True)
    retired_date = models.DateField(max_length=1024, null=True, blank=True)
    hosting = models.IntegerField(choices=HostingType.choices, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self) -> str:
        return self.name