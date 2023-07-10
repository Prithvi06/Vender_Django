from django.contrib import admin
from . models import Risk, RiskAuditHistory
# Register your models here.


admin.site.register(Risk)

admin.site.register(RiskAuditHistory)