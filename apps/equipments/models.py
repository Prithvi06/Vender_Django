from django.db import models
from organizations.models import Organization
from apps.vendor.models import Vendor

# Create your models here.


class Equipment(models.Model):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=1024)
    equipment_type = models.CharField(max_length=1024)
    asset_id = models.CharField(max_length=1024)
    serial_num = models.CharField(max_length=1024, null=True, blank=True)
    vendor = models.CharField(max_length=1024, null=True, blank=True)
    inservice_date = models.DateField(max_length=1024, null=True, blank=True)
    retired_date = models.DateField(max_length=1024, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self) -> str:
        return self.name