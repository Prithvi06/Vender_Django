import math
import re
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AbstractUser
from django.db.models import Q, QuerySet
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.template import loader
from django.urls import reverse
from django.utils import timezone
from organizations.models import OrganizationUser
from pytz import timezone as time_zone

from apps.authentication.models import User
from apps.incidents.models import Incident
from apps.risks.models import Risk
from apps.tasks.tables import TaskTable
from apps.utility.EmailServices import send_mention_email
from apps.utility.VendorUtilities import get_mention_user, org_users
from apps.vendor.models import Contact, Contract, Vendor
from apps.vendor.views import get_user_org

from .forms import TaskForm
from .models import Task, TaskAuditHistory, TaskStatus

# Create your views here.


def get_priority(value):
    value = int(value)
    if value == 1:
        return "Low"
    elif value == 2:
        return "Medium"
    else:
        return "High"


def get_status(value):
    value = int(value)
    if value == 1:
        return "Not Started"
    elif value == 2:
        return "In Process"
    elif value == 3:
        return "On Hold"
    elif value == 4:
        return "Cancelled"
    else:
        return "Completed"


def org_tasks(user: AbstractUser) -> QuerySet:
    """get all task associated to user's org"""
    # If the user is None, has no ID or is not active
    # return an empty queryset
    if not user or not user.id or not user.is_active:
        return Task.objects.none()

    # find only orgs that the user is associated to and that
    # are active
    orgs = [
        o.organization
        for o in OrganizationUser.objects.filter(user_id=user.id).select_related("organization")
        if o.organization.is_active
    ]
    org_user = OrganizationUser.objects.filter(user=user).first()
    tasks = Task.objects.filter(org__in=orgs).exclude(is_deleted=True)
    if org_user:
        if not org_user.is_admin:
            tasks = tasks.filter(Q(created_by_user=user) | Q(owner=user))
    return tasks


def get_task_status_value(data):
    """get all unique task status"""
    data = data.values_list("status", flat=True)
    unique = set(data)
    result = list(unique)
    result.sort()
    result = {str(value): get_status(value) for value in result}
    return result


def get_task_resources(org):
    """get all unique linked resource from all tables"""
    data = []
    vendor_data = Vendor.objects.filter(org=org).distinct()
    contact_list = []
    vendor_list = []
    contract_list = []
    risk_list = []
    incident_list = []
    for vendor in vendor_data:
        vendor_list.append({"table": "VENDOR", "id": vendor.id, "value": vendor.name})
    contact_data = Contact.objects.filter(vendor__org=org).distinct()
    for contact in contact_data:
        contact_list.append(
            {"table": "CONTACT", "id": contact.vendor.id, "value": f"{contact.first_name} {contact.last_name}"}
        )
    contract_data = Contract.objects.filter(vendor__org=org).distinct()
    for contract in contract_data:
        contract_list.append({"table": "CONTRACT", "id": contract.vendor.id, "value": contract.title})
    risk_data = Risk.objects.filter(org=org).distinct()
    for risk in risk_data:
        risk_list.append({"table": "RISK", "id": risk.id, "value": risk.title})
    incident_data = Incident.objects.filter(org=org).distinct()
    for incident in incident_data:
        incident_list.append({"table": "INCIDENT", "id": incident.id, "value": incident.title})
    return vendor_list, contact_list, contract_list, risk_list, incident_list


@login_required
def tasks(request):
    """task view"""
    sort = request.GET.get("sort", "title")
    page = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 15)
    search = request.GET.get("search", "")
    param = request.GET.get("param", None)
    filter_by = request.GET.get("filter_by", None)
    search_mine = request.GET.get("self", None)

    # initial data shows all task for all orgs that user belongs to
    # then filter it down to only owned/created_by if the they are not admin
    user = request.user
    data = org_tasks(user)
    status_values = get_task_status_value(data)
    org_user = OrganizationUser.objects.filter(user=user).first()
    if org_user:
        if not org_user.is_admin:
            data = data.filter(Q(created_by_user=user) | Q(owner=user))

    if search:
        data_by_title = data.filter(title__icontains=search)
        data_by_owner = data.filter(owner__first_name__icontains=search)
        data_by_resources = data.filter(linked_resources__icontains=search)
        data = (data_by_title | data_by_resources | data_by_owner).distinct()
    if search_mine == "True":
        data = data.filter(owner=request.user)
    if param:
        if filter_by == "status":
            data = data.filter(status=param)
        elif filter_by == "owner":
            data = data.filter(owner_id=param)
        elif filter_by == "date":
            today = timezone.now().date()
            next_week = [today, today + timedelta(days=7)]
            last_30 = today - timedelta(days=30)
            if param == "past_due":
                data = data.filter(due_date__lt=today)
            elif param == "due_this_week":
                data = data.filter(due_date__range=next_week)
            elif param == "stale":
                data = data.filter(due_date=None, created_at__date__lte=last_30)
    table = TaskTable(data=data, order_by=sort)
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
    table = TaskTable(data=data, order_by=sort, template_name="table/custome_table.html")
    table.paginate(page=page, per_page=page_size)
    context = {
        "segment": "tasks",
        "tabledata": table,
        "search": search,
        "organization": get_user_org(request.user),
        "organization_pk": get_user_org(request.user).id if get_user_org(request.user) else "",
        "status": status_values,
        "tasks": org_tasks(request.user).exclude(owner=None).order_by("owner").distinct("owner"),
    }
    return HttpResponse(loader.get_template("tasks/index.html").render(context, request))


def taskRender(risk_id=None, incident_id=None, vendor_id=None, parent_task_id=None):
    if risk_id:
        return HttpResponseRedirect(reverse("risk-edit", args=[risk_id]))
    elif incident_id:
        return HttpResponseRedirect(reverse("incident-edit", args=[incident_id]))
    elif vendor_id:
        return HttpResponseRedirect(reverse("vendor-edit", args=[vendor_id]))
    elif parent_task_id:
        return HttpResponseRedirect(reverse("task-edit", args=[parent_task_id]))
    else:
        return HttpResponseRedirect(reverse("tasks"))


@login_required
def task_view(
    request,
    task_id: int = None,
    risk_id: int = None,
    incident_id: int = None,
    vendor_id: int = None,
    parent_task_id: int = None,
):
    """task view"""
    sagment = "tasks"
    risk = None
    incident = None
    vendor = None
    parent_task = None
    resource_val = ""
    resource_display = False
    if risk_id:
        risk = Risk.objects.get(pk=risk_id)
        sagment = "risks"
    elif incident_id:
        incident = Incident.objects.get(pk=incident_id)
        sagment = "incidents"
    elif vendor_id:
        vendor = Vendor.objects.get(pk=vendor_id)
        sagment = "vendors"
    elif parent_task_id:
        parent_task = Task.objects.get(id=parent_task_id)
    notes = ""
    model = get_object_or_404(org_tasks(request.user), pk=task_id) if task_id else Task(org=None)
    audit_history: list[TaskAuditHistory] = TaskAuditHistory.objects.filter(task_id=task_id)
    model.org = model.org if hasattr(model, "org") else get_user_org(request.user)
    tasks = Task.objects.filter(parent_task=model).exclude(is_deleted=True)
    created_at = (
        str(model.created_at.astimezone(time_zone("US/Pacific")).strftime("%m/%d/%y %I:%M %p"))
        if task_id
        else str(timezone.now().astimezone(time_zone("US/Pacific")).strftime("%m/%d/%y %I:%M %p"))
    )
    closed_date = "--"
    if task_id:
        if (model.status == TaskStatus.COMPLETED) and model.closed_date:
            closed_date = str(model.closed_date.astimezone(time_zone("US/Pacific")).strftime("%m/%d/%y %I:%M %p"))
    if request.method == "POST":
        model.created_by_user = request.user
        if task_id:
            task_object = Task.objects.get(pk=task_id)
            model_field = task_object.__dict__
        form = TaskForm(request.POST, model=model, instance=model)
        if form.is_valid():
            if "description" in form.changed_data:
                users = get_mention_user(request.POST["description"])
                if task_id:
                    prev_users = get_mention_user(task_object.description)
                    if prev_users:
                        users = [i for i in users if i not in prev_users]
                send_mention_email(
                    users,
                    "Task",
                    f"{request.user.first_name} {request.user.last_name}",
                    request.POST["title"],
                    request.POST["description"],
                )
            if "status" in form.changed_data:
                if request.POST["status"] == str(TaskStatus.COMPLETED):
                    if not model.closed_date:
                        model.closed_date = datetime.now()
            model = form.save(commit=False)
            if risk_id:
                model.risk_id = risk_id
                model.linked_resources = risk.title
            elif incident_id:
                model.incident_id = incident_id
                model.linked_resources = incident.title
            elif vendor_id:
                model.vendor_id = vendor_id
            elif parent_task_id:
                model.parent_task_id = parent_task_id
            else:
                if model.linked_resources:
                    linked_resource = model.linked_resources.split("#")
                    if len(linked_resource) > 1:
                        table = linked_resource[0]
                        table_id = linked_resource[1]
                        if table in ["VENDOR", "CONTACT", "CONTRACT"]:
                            vendor = Vendor.objects.filter(id=table_id)
                            if vendor.exists():
                                model.vendor = vendor.first()
                        elif table == "RISK":
                            risk = Risk.objects.filter(id=table_id)
                            if risk.exists():
                                model.risk = risk.first()
                        elif table == "INCIDENT":
                            incident = Incident.objects.filter(id=table_id)
                            if incident.exists():
                                model.incident = incident.first()
            model.save()
            history = model.history.filter(pk=model.history.latest().pk).update(history_user=request.user)
            return taskRender(risk_id, incident_id, vendor_id, parent_task_id)
    elif request.path.endswith("delete"):
        Task.objects.filter(pk=model.id).update(is_deleted=True)
        return taskRender(risk_id, incident_id, vendor_id, parent_task_id)
    else:
        form = TaskForm(model=model, initial=model.__dict__)
        if model.id:
            notes = (model.description).replace(
                "https://sanctionssearch.ofac.treas.gov/",
                "<a contenteditable='false' target='_blank' href='https://sanctionssearch.ofac.treas.gov/'>https://sanctionssearch.ofac.treas.gov/</a>",
            )
        if risk_id or model.risk:
            form.fields["linked_resources"].widget.attrs["value"] = risk
            resource_val = risk
            resource_display = True
        elif incident or model.incident:
            form.fields["linked_resources"].widget.attrs["value"] = incident
            resource_val = incident
            resource_display = True
        elif parent_task_id or model.parent_task:
            form.fields["linked_resources"].widget.attrs["value"] = parent_task
            resource_val = parent_task
            resource_display = True
        elif vendor_id or model.vendor:
            form.fields["linked_resources"].widget.attrs["value"] = vendor
            resource_val = vendor
            resource_display = True
    linked_data = get_task_resources(get_user_org(request.user))
    if model.id:
        if model.linked_resources:
            resource_val = model.linked_resources.split("#")
            if len(resource_val) > 1:
                resource_val = resource_val[2]
            else:
                resource_val = model.linked_resources
    context = {
        "segment": sagment,
        "form": form,
        "model": model,
        "organization": get_user_org(request.user),
        "audit_history": audit_history,
        "created_at": created_at,
        "risk": risk,
        "incident": incident,
        "vendor": vendor,
        "notes": notes,
        "vendor_list": linked_data[0],
        "contact_list": linked_data[1],
        "contract_list": linked_data[2],
        "risk_list": linked_data[3],
        "incident_list": linked_data[4],
        "resource_val": resource_val,
        "tasks": tasks,
        "resource_display": resource_display,
        "parent_task_id": parent_task_id,
        "users": org_users(request.user),
        "closed_date": closed_date,
    }

    return render(request, "tasks/task_form.html", context)
