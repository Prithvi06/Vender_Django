import math

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AbstractUser
from django.db.models import QuerySet
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.template import loader
from django.urls import reverse
from organizations.models import OrganizationUser

from apps.incidents.tables import IncidentTable
from apps.tasks.models import Task
from apps.utility.EmailServices import send_mention_email
from apps.utility.VendorUtilities import get_mention_user, org_users, org_vendors
from apps.vendor.views import get_user_org

from .forms import IncidentForm
from .models import Incident

# Create your views here.


def get_status(value):
    value = int(value)
    if value == 1:
        return "Reported"
    elif value == 2:
        return "Active"
    elif value == 3:
        return "Extended Remediation"
    elif value == 4:
        return "Closed"
    else:
        return "Not An Incident"


def org_incidents(user: AbstractUser) -> QuerySet:
    """get all incident associated to user's org"""
    # If the user is None, has no ID or is not active
    # return an empty queryset
    if not user or not user.id or not user.is_active:
        return Incident.objects.none()

    # find only orgs that the user is associated to and that
    # are active
    orgs = [
        o.organization
        for o in OrganizationUser.objects.filter(user_id=user.id).select_related("organization")
        if o.organization.is_active
    ]
    return Incident.objects.filter(org__in=orgs)


def get_incident_status_value(data):
    """get all unique incident status"""
    data = data.values_list("status", flat=True)
    unique = set(data)
    result = list(unique)
    result.sort()
    result = {str(value): get_status(value) for value in result}
    return result


def get_resource_option_list_vendor(user):
    """get all unique vendor and business process"""
    vendor_data = list(org_vendors(user).values_list("name", flat=True))
    data = vendor_data
    unique = set(data)
    result = list(unique)
    result.sort()
    return result


def get_resource_option_list_vendor_process(user):
    """get all unique vendor and business process"""
    business_data = list(
        org_vendors(user).exclude(org_business_process=None).values_list("org_business_process", flat=True)
    )
    data = business_data
    unique = set(data)
    result = list(unique)
    result.sort()
    return result


@login_required
def incidents(request):
    """incident view"""
    sort = request.GET.get("sort", "title")
    page = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 15)
    search = request.GET.get("search", "")
    status = request.GET.get("status", None)
    data = org_incidents(request.user)
    status_values = get_incident_status_value(data)
    if search:
        data = data.filter(title__icontains=search)

    if status:
        data = data.filter(status=status)

    table = IncidentTable(data=data, order_by=sort)
    total_data = data.count()
    if page_size == "All":
        page = 1
        page_size = total_data
    elif total_data < int(page_size) * int(page) and total_data != 0:
        if total_data > (int(page_size) * (int(page) - 1)):
            pass
        else:
            page_size = total_data
            page = int(math.ceil(int(page_size) * int(page) % total_data))
            if page <= 0:
                page = 1
    table = IncidentTable(data=data, order_by=sort, template_name="table/custome_table.html")
    table.paginate(page=page, per_page=page_size)

    context = {
        "segment": "incidents",
        "tabledata": table,
        "search": search,
        "organization": get_user_org(request.user),
        "organization_pk": get_user_org(request.user).id if get_user_org(request.user) else "",
        "status": status_values,
    }
    return HttpResponse(loader.get_template("incidents/index.html").render(context, request))


@login_required
def incident_view(request, incident_id: int = None):
    """incident view"""
    model = get_object_or_404(org_incidents(request.user), pk=incident_id) if incident_id else Incident(org=None)
    tasks = []
    if model.id:
        tasks: list[Task] = model.task_set.exclude(is_deleted=True)
    model.org = model.org if hasattr(model, "org") else get_user_org(request.user)
    incident_object = Incident.objects.filter(id=incident_id)
    if request.method == "POST":
        form = IncidentForm(request.POST, model=model, instance=model)
        if form.is_valid():
            if "root_cause" in form.changed_data:
                users = get_mention_user(request.POST["root_cause"])
                if incident_object:
                    prev_users = get_mention_user(incident_object.first().root_cause)
                    if prev_users:
                        users = [i for i in users if i not in prev_users]
                send_mention_email(
                    users,
                    "Incident",
                    f"{request.user.first_name} {request.user.last_name}",
                    request.POST["title"],
                    request.POST["root_cause"],
                )
            if "description" in form.changed_data:
                users = get_mention_user(request.POST["description"])
                if incident_object:
                    prev_users = get_mention_user(incident_object.first().description)
                    if prev_users:
                        users = [i for i in users if i not in prev_users]
                send_mention_email(
                    users,
                    "Incident",
                    f"{request.user.first_name} {request.user.last_name}",
                    request.POST["title"],
                    request.POST["description"],
                )
            model = form.save(commit=False)
            model.save()
            history = model.history.filter(pk=model.history.latest().pk).update(history_user=request.user)
            return HttpResponseRedirect(reverse("incidents"))
    else:
        form = IncidentForm(model=model, initial=model.__dict__)

    context = {
        "segment": "incidents",
        "form": form,
        "model": model,
        "organization": get_user_org(request.user),
        "tasks": tasks,
        "resource_option_vendor": get_resource_option_list_vendor(request.user),
        "resource_option_process": get_resource_option_list_vendor_process(request.user),
        "users": org_users(request.user),
    }

    return render(request, "incidents/incident_form.html", context)
