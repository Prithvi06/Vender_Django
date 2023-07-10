from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AbstractUser
from django.db.models import F
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template import loader
from django.urls import reverse
from organizations.models import OrganizationUser

from apps.incidents.models import Incident
from apps.notes.models import CommentsLog
from apps.risks.models import Risk
from apps.tasks.models import Task
from apps.utility.EmailServices import send_mention_email
from apps.utility.VendorUtilities import get_mention_user, org_users
from apps.vendor.models import Contact, VendorSurvey
from apps.vendor.views import get_user_org

# Create your views here.
# Blank comment to force a build and deploy.


@login_required
def notes(request):
    if request.method == "POST":
        notes = CommentsLog.objects.create(comment=request.POST["comment"], author=request.user)
    notes = list(CommentsLog.objects.all().values())
    context = {"segment": "notes", "organization": get_user_org(request.user), "notes": notes}
    return HttpResponse(loader.get_template("notes/index.html").render(context, request))


@login_required
def log_comments(request, id=None, task_id=None, contact_id=None, incident_id=None, risk_id=None, survey_id=None):
    if request.method == "POST":
        task = Task.objects.filter(pk=task_id)
        contact = Contact.objects.filter(pk=contact_id)
        incident = Incident.objects.filter(pk=incident_id)
        risk = Risk.objects.filter(pk=risk_id)
        survey = VendorSurvey.objects.filter(pk=survey_id)
        if contact_id:
            title = f"{contact.first().first_name} {contact.first().last_name}"
            obj_type = "Contact"
        elif incident_id:
            title = incident.first().title
            obj_type = "Incident"
        elif risk_id:
            title = risk.first().title
            obj_type = "Risk"
        elif survey_id:
            title = survey.first().name
            obj_type = "Questionnaire"
        else:
            title = task.first().title
            obj_type = "Task"
        if id:
            notes = CommentsLog.objects.filter(author=request.user, id=id)
            if request.POST["comment"] != notes.first().comment:
                users = get_mention_user(request.POST["comment"])
                prev_users = get_mention_user(notes.first().comment)
                if prev_users:
                    users = [i for i in users if i not in prev_users]
                send_mention_email(
                    users,
                    obj_type,
                    f"{request.user.first_name} {request.user.last_name}",
                    title,
                    request.POST["comment"],
                )
            notes.update(
                comment=request.POST["comment"].strip(), risk_id=risk_id, task_id=task_id, incident_id=incident_id, contact_id=contact_id, survey_id=survey_id
            )
        else:
            notes = CommentsLog.objects.create(
                task_id=task_id,
                contact_id=contact_id,
                comment=request.POST["comment"].strip(),
                author=request.user,
                incident_id=incident_id,
                risk_id=risk_id,
                survey_id=survey_id,
            )
            users = get_mention_user(request.POST["comment"])
            send_mention_email(
                users,
                obj_type,
                f"{request.user.first_name} {request.user.last_name}",
                title,
                request.POST["comment"],
            )
    notes = list(
        CommentsLog.objects.filter(task_id=task_id, incident_id=incident_id, contact_id=contact_id, risk_id=risk_id, survey_id=survey_id)
        .annotate(author_first_name=F("author__first_name"), author_last_name=F("author__last_name"))
        .order_by("created_at")
        .values()
    )
    return JsonResponse({"data": notes})
