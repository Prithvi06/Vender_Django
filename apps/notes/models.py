from django.db import models
from apps.authentication.models import User as AuthUser
from apps.tasks.models import Task
from apps.vendor.models import Contact, VendorSurvey
from apps.incidents.models import Incident
from apps.risks.models import Risk

# Create your models here.


class CommentsLog(models.Model):
    author = models.ForeignKey(AuthUser, on_delete=models.CASCADE)
    comment = models.TextField(null=True, blank=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, null=True, blank=True)
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, null=True, blank=True)
    risk = models.ForeignKey(Risk, on_delete=models.CASCADE, null=True, blank=True)
    survey = models.ForeignKey(VendorSurvey, on_delete=models.CASCADE, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
