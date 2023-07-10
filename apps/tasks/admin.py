from django.contrib import admin
from . models import Task, TaskAuditHistory
# Register your models here.


admin.site.register(Task)

admin.site.register(TaskAuditHistory)