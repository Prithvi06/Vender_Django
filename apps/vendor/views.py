# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import json
import math
import mimetypes
import os
from datetime import datetime, timedelta
from typing import OrderedDict
from uuid import uuid4
from uuid_extensions import uuid7, uuid7str
import random
import string

import pandas as pd
import pytz
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AbstractUser
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Case, CharField, Count, F, Func, Q, Sum, Value, When
from django.http import (
    HttpResponse,
    HttpResponseNotFound,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from organizations.models import Organization, OrganizationUser

from apps.authentication.models import DocumentPermission, User
from apps.incidents.models import (
    INCIDENT_STATUS_DISPLAYNAMES,
    SEVERITY_DISPLAYNAMES,
    Incident,
    IncidentStatus,
)
from apps.tasks.models import TASK_STATUS_DISPLAYNAMES, Task, TaskStatus
from apps.utility.EmailServices import send_mention_email, send_survey_link, send_survey_password
from apps.utility.VendorUtilities import (
    SEARCH_MINE,
    get_contract_activity,
    get_mention_user,
    org_users,
    org_vendors,
)
from apps.vendor.tables import ContractTable, VendorTable

from .forms import (
    TRUE_FALSE_CHOICES,
    ContactForm,
    ContractForm,
    DocumentForm,
    PhoneForm,
    VendorForm,
    get_vendor_categories,
)
from .fusioncharts import FusionCharts
from .models import (
    RISK_GRADE_DISPLAYNAMES,
    VENDOR_STATUS_DISPLAYNAMES,
    Contact,
    ContactRole,
    Contract,
    Document,
    Phone,
    Vendor,
    get_status,
    VendorSurvey,
    VendorSurveyQuestion,
    VendorSurveyUserAnswer,
    VendorSurveyAnswer,
    SurveyToken,
)
from .tasks import contact_report, contact_search, vendor_report, vendor_search
from apps.authentication.models import DocumentPermission
from django.db.models import F, Func, Value, CharField, Q
from apps.djf_surveys.models import Survey, Question, OrgSurvey, OrgQuestion, QuestionHeader, SurveyStatus
from apps.incidents.models import Incident
from django.contrib.auth.hashers import make_password

CHART_WIDTH = "100%"
CHART_HEIGHT = 380


def get_superseded_by_ids(data, contracts, obj):
    contracts = contracts.exclude(id=data.id)
    try:
        if data.superseded_by:
            get_superseded_by_ids(data.superseded_by, contracts, data)
        return contracts
    except Exception as e:
        return contracts


def isOrgAdmin(user):
    if not user or not user.id or not user.is_active:
        return False
    orguser = OrganizationUser.objects.filter(user=user).first()
    if orguser.is_admin:
        return True
    else:
        return False


def get_document_permission(user, vendor):
    if not user or not user.id or not user.is_active:
        return False
    if (isOrgAdmin(user)) or (
        (user.document_permission in [DocumentPermission.EDIT_OWNED, DocumentPermission.VIEW_OWNED])
        and (vendor.owner == user)
        or (user.document_permission in [DocumentPermission.EDIT_ALL, DocumentPermission.VIEW_ALL])
    ):
        return True
    else:
        return False


def get_edit_document_permission(user, vendor):
    if not user or not user.id or not user.is_active:
        return False
    if (isOrgAdmin(user)) or (
        (user.document_permission in [DocumentPermission.EDIT_OWNED])
        and (vendor.owner == user)
        or (user.document_permission in [DocumentPermission.EDIT_ALL])
    ):
        return True
    else:
        return False


def get_user_org(user: AbstractUser) -> Organization:
    """get first org user is associated to"""
    if not user or not user.id or not user.is_active:
        return None

    orguser = OrganizationUser.objects.select_related("organization").filter(user=user).first()
    return orguser.organization if orguser else None


def get_relationships_chart(user: AbstractUser, target_element: str, search: str = None):
    """get relationships chart for dashboards"""
    query = org_vendors(user).exclude(status=None).values("status").annotate(dcount=Count("status")).order_by("status")
    if search == SEARCH_MINE:
        query = (
            org_vendors(user)
            .filter(owner=user)
            .exclude(status=None)
            .values("status")
            .annotate(dcount=Count("status"))
            .order_by("status")
        )
    data = [{"label": VENDOR_STATUS_DISPLAYNAMES[i["status"]], "value": i["dcount"]} for i in query]
    total = query.aggregate(Sum("dcount"))["dcount__sum"]

    datasource: dict = OrderedDict()
    datasource["chart"] = OrderedDict()
    datasource["chart"]["theme"] = "fusion"
    datasource["chart"]["defaultcenterlabel"] = f"{total}<br>Third Parties"
    datasource["chart"]["showLegend"] = "0"
    datasource["chart"]["caption"] = "Third Parties by Status"
    datasource["chart"]["showPercentValues"] = "0"
    datasource["data"] = data
    chart = FusionCharts("doughnut2d", "relationships", CHART_WIDTH, CHART_HEIGHT, target_element, "json", datasource)
    chart.addEvent("dataPlotClick", "plotClickHandler")
    return chart


def get_risk_chart(user: AbstractUser, target_element: str, search: str = None):
    """get risk chart for dashboards"""
    query = (
        org_vendors(user)
        .exclude(residual_risk=None)
        .values("residual_risk")
        .annotate(dcount=Count("residual_risk"))
        .order_by("residual_risk")
    )
    if search == SEARCH_MINE:
        query = (
            org_vendors(user)
            .filter(owner=user)
            .exclude(residual_risk=None)
            .values("residual_risk")
            .annotate(dcount=Count("residual_risk"))
            .order_by("residual_risk")
        )
    data = [{"label": RISK_GRADE_DISPLAYNAMES[i["residual_risk"]], "value": i["dcount"]} for i in query]

    datasource: dict = OrderedDict()
    datasource["chart"] = OrderedDict()
    datasource["chart"]["theme"] = "fusion"
    datasource["chart"]["defaultcenterlabel"] = "Residual Risk"
    datasource["chart"]["showLegend"] = "0"
    datasource["chart"]["caption"] = "Third Parties by Residual Risk"
    datasource["chart"]["decimals"] = ("0",)
    datasource["data"] = data

    chart = FusionCharts("doughnut2d", "risk", CHART_WIDTH, CHART_HEIGHT, target_element, "json", datasource)
    chart.addEvent("dataPlotClick", "riskPlotClickHandler")
    return chart


def get_top_categories_chart(user: AbstractUser, target_element: str, search: str = None):
    """get top categories chart for dashboards"""
    query = (
        org_vendors(user)
        .exclude(category=None)
        .values("category")
        .annotate(dcount=Count("category"))
        .order_by("-dcount")[:12]
    )
    if search == SEARCH_MINE:
        query = (
            org_vendors(user)
            .filter(owner=user)
            .exclude(category=None)
            .values("category")
            .annotate(dcount=Count("category"))
            .order_by("-dcount")[:12]
        )
    data = [{"label": i["category"], "value": i["dcount"]} for i in query]

    datasource: dict = OrderedDict()
    datasource["chart"] = OrderedDict()
    datasource["chart"]["theme"] = "fusion"
    datasource["chart"]["defaultcenterlabel"] = "Top Categories"
    datasource["chart"]["showLegend"] = "0"
    datasource["chart"]["caption"] = "Top Third Party Categories"
    datasource["chart"]["showPercentValues"] = ("0",)
    datasource["data"] = data

    chart = FusionCharts("doughnut2d", "categories", CHART_WIDTH, CHART_HEIGHT, target_element, "json", datasource)
    chart.addEvent("dataPlotClick", "categoryPlotClickHandler")
    return chart


def get_incident_chart(user: AbstractUser, target_element: str):
    """get incident chart for dashboards"""
    from apps.incidents.views import org_incidents

    query = org_incidents(user).values("status").annotate(dcount=Count("status")).order_by("status")
    data = [{"label": INCIDENT_STATUS_DISPLAYNAMES[i["status"]], "value": i["dcount"]} for i in query]
    total = query.aggregate(Sum("dcount"))["dcount__sum"]

    datasource: dict = OrderedDict()
    datasource["chart"] = OrderedDict()
    datasource["chart"]["theme"] = "fusion"
    datasource["chart"]["defaultcenterlabel"] = f"{total}<br> Incidents"
    datasource["chart"]["showLegend"] = "0"
    datasource["chart"]["caption"] = "Incidents by Status"
    datasource["chart"]["showPercentValues"] = "0"
    datasource["data"] = data

    chart = FusionCharts("doughnut2d", "incident", CHART_WIDTH, CHART_HEIGHT, target_element, "json", datasource)
    chart.addEvent("dataPlotClick", "incidentPlotClickHandler")
    return chart


def get_task_chart(user: AbstractUser, target_element: str, search: str = None):
    """get relationships chart for dashboards"""
    from apps.tasks.views import org_tasks

    query = (
        org_tasks(user)
        .exclude(status=TaskStatus.CANCELLED)
        .values("status")
        .annotate(dcount=Count("status"))
        .order_by("status")
    )
    if search == SEARCH_MINE:
        query = (
            org_tasks(user)
            .filter(owner=user)
            .exclude(status=TaskStatus.CANCELLED)
            .values("status")
            .annotate(dcount=Count("status"))
            .order_by("status")
        )
    data = [{"label": TASK_STATUS_DISPLAYNAMES[i["status"]], "value": i["dcount"]} for i in query]
    total = query.aggregate(Sum("dcount"))["dcount__sum"]

    datasource: dict = OrderedDict()
    datasource["chart"] = OrderedDict()
    datasource["chart"]["theme"] = "fusion"
    datasource["chart"]["defaultcenterlabel"] = f"{total}<br> Tasks"
    datasource["chart"]["showLegend"] = "0"
    datasource["chart"]["caption"] = "Tasks By Status"
    datasource["chart"]["showPercentValues"] = "0"
    datasource["data"] = data

    chart = FusionCharts("doughnut2d", "tasks", CHART_WIDTH, CHART_HEIGHT, target_element, "json", datasource)
    chart.addEvent("dataPlotClick", "taskPlotClickHandler")
    return chart


def get_rating_query(query):
    low = [i for i in range(1, 6)]
    medium = [i for i in range(6, 11)]
    high = [i for i in range(11, 26)]
    rating_query = []
    low_rating = query.filter(rating__in=low).aggregate(Sum("dcount"))["dcount__sum"]
    medium_rating = query.filter(rating__in=medium).aggregate(Sum("dcount"))["dcount__sum"]
    high_rating = query.filter(rating__in=high).aggregate(Sum("dcount"))["dcount__sum"]
    if low_rating != 0:
        rating_query.append({"rating": "Low", "count": low_rating})
    if medium_rating != 0:
        rating_query.append({"rating": "Medium", "count": medium_rating})
    if high_rating != 0:
        rating_query.append({"rating": "High", "count": high_rating})
    return rating_query


def get_risk_items_chart(user: AbstractUser, target_element: str, search: str = None):
    """get risk items chart for dashboards"""
    from apps.risks.views import org_risks

    query = org_risks(user).values("rating").annotate(dcount=Count("rating")).order_by("rating")
    if search == SEARCH_MINE:
        query = org_risks(user).filter(owner=user).values("rating").annotate(dcount=Count("rating")).order_by("rating")
    data = [{"label": i["rating"], "value": i["count"]} for i in get_rating_query(query)]
    total = query.aggregate(Sum("dcount"))["dcount__sum"]

    datasource: dict = OrderedDict()
    datasource["chart"] = OrderedDict()
    datasource["chart"]["theme"] = "fusion"
    datasource["chart"]["defaultcenterlabel"] = f"{total}<br> Risk Items"
    datasource["chart"]["showLegend"] = "0"
    datasource["chart"]["caption"] = "Risk Items by Score"
    datasource["chart"]["showPercentValues"] = "0"
    datasource["data"] = data

    chart = FusionCharts("doughnut2d", "risk_items", CHART_WIDTH, CHART_HEIGHT, target_element, "json", datasource)
    chart.addEvent("dataPlotClick", "risksPlotClickHandler")
    return chart


def get_risk_rating(user, search):
    from apps.risks.views import org_risks

    if search == SEARCH_MINE:
        risk = (
            org_risks(user)
            .filter(owner=user)
            .values("rating", "impact", "likelihood")
            .annotate(total_rating=Count("rating"))
            .order_by("rating")
        )
    else:
        risk = (
            org_risks(user)
            .values("rating", "impact", "likelihood")
            .annotate(total_rating=Count("rating"))
            .order_by("rating")
        )
    return list(risk)


@login_required
def dashboard(request):
    """dashboard view page"""
    from apps.tasks.views import org_tasks

    search = request.GET.get("search", None)
    render_category_chart = True
    render_relationships_chart = True
    render_risk_chart = True
    render_risk_items_chart = True
    render_incident_chart = True
    render_task_chart = True
    relationships_chart = get_relationships_chart(request.user, "relationships-chart", search)
    risk_chart = get_risk_chart(request.user, "risk-chart", search)
    top_categories_chart = get_top_categories_chart(request.user, "top-categories-chart", search)
    contract_activity = get_contract_activity(request.user, search)
    risk_items_chart = get_risk_items_chart(request.user, "risk-items-chart", search)
    incident_chart = get_incident_chart(request.user, "incident-chart")
    task_chart = get_task_chart(request.user, "task-chart", search)
    if len(top_categories_chart.constructorOptions["dataSource"]["data"]) == 0:
        render_category_chart = False
    if len(relationships_chart.constructorOptions["dataSource"]["data"]) == 0:
        render_relationships_chart = False
    if len(risk_chart.constructorOptions["dataSource"]["data"]) == 0:
        render_risk_chart = False
    if len(risk_items_chart.constructorOptions["dataSource"]["data"]) == 0:
        render_risk_items_chart = False
    if len(incident_chart.constructorOptions["dataSource"]["data"]) == 0:
        render_incident_chart = False
    if len(task_chart.constructorOptions["dataSource"]["data"]) == 0:
        render_task_chart = False

    tasks = list(
        org_tasks(request.user)
        .annotate(
            start=Func(F("due_date"), Value("yyyy-MM-dd"), function="to_char", output_field=CharField()),
            due_show_date=Func(F("due_date"), Value("MM/dd/yyyy"), function="to_char", output_field=CharField()),
            initial_date=Func(F("created_at"), Value("yyyy-MM-dd"), function="to_char", output_field=CharField()),
        )
        .values("title", "start", "status", "initial_date", "pk", "due_show_date")
    )
    vendor_list = org_vendors(request.user)
    document_form = DocumentForm()
    cont_document_form = DocumentForm()
    document_form.fields["path"].widget.attrs["id"] = "id_path_doc"
    document_form.fields["description"].widget.attrs["required"] = "true"
    cont_document_form.fields["path"].widget.attrs["id"] = "id_path_contract"
    popup_contract_from = ContractForm()

    context = {
        "segment": "dashboard",
        "organization": get_user_org(request.user),
        "relationships_chart": relationships_chart.render(),
        "risk_chart": risk_chart.render(),
        "top_categories_chart": top_categories_chart.render(),
        "contract_activity": contract_activity,
        "incident_chart": incident_chart.render(),
        "risk_items_chart": risk_items_chart.render(),
        "task_chart": task_chart.render(),
        "search": search,
        "risk_rating": json.dumps(get_risk_rating(request.user, search)),
        "render_category_chart": render_category_chart,
        "render_relationships_chart": render_relationships_chart,
        "render_risk_chart": render_risk_chart,
        "render_risk_items_chart": render_risk_items_chart,
        "render_incident_chart": render_incident_chart,
        "render_task_chart": render_task_chart,
        "tasks": tasks,
        "document_form": document_form,
        "popup_contract_from": popup_contract_from,
        "vendor_list": vendor_list,
        "cont_document_form": cont_document_form,
    }

    return render(request, "vendors/dashboard.html", context)


def get_residual_risk(value):
    value = int(value)
    if value == 1:
        return "Low"
    elif value == 2:
        return "Medium"
    elif value == 3:
        return "High"
    else:
        return "None"


def get_vendor_status(value):
    value = int(value)
    if value == 1:
        return "Proposal"
    elif value == 2:
        return "Active"
    elif value == 3:
        return "Terminated"
    else:
        return "Not Engaged"


def get_residual_risk_value(data):
    """get all unique vendor residual risk"""
    data = data.values_list("residual_risk", flat=True)
    unique = set(data)
    result = list(unique)
    result.sort()
    result = {str(value): get_residual_risk(value) for value in result}
    return result


def get_status_values(data):
    """get all unique vendor status"""
    data = data.values_list("status", flat=True).exclude(status=None)
    unique = set(data)
    result = list(unique)
    result.sort()
    result = {str(value): get_vendor_status(value) for value in result}
    return result


@login_required
def vendors(request):
    """vendors view"""
    sort = request.GET.get("sort", "name")
    page = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 15)
    search = request.GET.get("search", "")
    filter_by = request.GET.get("filter_by", None)
    param = request.GET.get("param", None)
    search_mine = request.GET.get("self", None)

    data = org_vendors(request.user).prefetch_related("contract_set").all()
    residual_risk = get_residual_risk_value(data)
    status_values = get_status_values(data)
    contract_activity = get_contract_activity(request.user)
    has_minimums = data.filter(contract__has_minimum_fees=True)
    auto_renews = data.filter(contract__is_auto_renew=True)
    if search:
        data = data.filter(name__icontains=search)
    if search_mine == "True":
        data = data.filter(owner=request.user)
    if param:
        if filter_by == "status":
            data = data.filter(status=get_status(param))
        elif filter_by == "risk":
            data = data.filter(residual_risk=param)
        elif filter_by == "category":
            data = data.filter(category=param)
        elif filter_by == "contract":
            if param == "has_minimums":
                data = has_minimums
            elif param == "auto_renews":
                data = auto_renews
            else:
                data = data.filter(contract__in=get_contract_activity(request.user, search)[param]).distinct()
        elif filter_by == "owner":
            data = data.filter(owner_id=param).distinct()
    table = VendorTable(data=data, order_by=sort, user=request.user)
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
    table = VendorTable(data=data, order_by=sort, template_name="table/custome_table.html", user=request.user)
    table.paginate(page=page, per_page=page_size)
    vendor_list = org_vendors(request.user)
    document_form = DocumentForm()
    cont_document_form = DocumentForm()
    document_form.fields["path"].widget.attrs["id"] = "id_path_doc"
    document_form.fields["description"].widget.attrs["required"] = "true"
    cont_document_form.fields["path"].widget.attrs["id"] = "id_path_contract"
    popup_contract_from = ContractForm()
    context = {
        "segment": "vendors",
        "tabledata": table,
        "search": search,
        "organization": get_user_org(request.user),
        "organization_pk": get_user_org(request.user).id if get_user_org(request.user) else "",
        "category": get_vendor_categories(get_user_org(request.user)),
        "residual_risk": residual_risk,
        "status": status_values,
        "contract_activity": contract_activity,
        "vendors": org_vendors(request.user).exclude(owner=None).order_by("owner").distinct("owner"),
        "has_minimums": has_minimums,
        "auto_renews": auto_renews,
        "document_form": document_form,
        "popup_contract_from": popup_contract_from,
        "vendor_list": vendor_list,
        "cont_document_form": cont_document_form,
    }
    return HttpResponse(loader.get_template("vendors/index.html").render(context, request))


def get_vendor_process(org):
    from apps.administrator.models import BusinessProcess
    org_business_process = BusinessProcess.objects.filter(organization=org)
    
    data = []
    if org_business_process:
            for udp_obj in org_business_process:
                if udp_obj.unit and udp_obj.department and udp_obj.process:
                    data.append((udp_obj.id, f"{udp_obj.unit.name} - {udp_obj.department.name} - {udp_obj.process.name}"))
    return data


@login_required
def vendor(request, vendor_id: int = None):
    """vendor view"""
    from apps.administrator.models import OFACSDNResult

    section = "TASK"
    ofac_results = None
    task_section = {}
    document_section = {}
    contact_section = {}
    contract_section = {}
    section_data = request.GET.get("section", "")
    if section_data:
        section = section_data
    model = get_object_or_404(org_vendors(request.user), pk=vendor_id) if vendor_id else Vendor(org=None)
    model.org = model.org if hasattr(model, "org") else get_user_org(request.user)

    # Contract section details
    contracts = []
    contacts = []
    tasks = []
    documents = []
    org_question = []
    vendor_survey = []
    vendor_survey_count = 0

    incident_objs = []
    open_questionnaire = []
    last_viewed = []
    if model.id:
        # quesionnaire section
        vendor_survey = VendorSurvey.objects.filter(vendor_id=vendor_id, active=True)
        for survey in vendor_survey:
            answer = VendorSurveyUserAnswer.objects.filter(vendor_id=vendor_id, survey=survey)
            if answer.exists():
                survey.answer = answer.first()
            else:
                survey.answer = None
        org_question = OrgSurvey.objects.filter(active=True, org=model.org)
        open_questionnaire = vendor_survey.exclude(status__in=[SurveyStatus.COMPLETED, SurveyStatus.CANCELLED]).count()
        last_viewed = (
            vendor_survey.exclude(status__in=[SurveyStatus.COMPLETED, SurveyStatus.CANCELLED])
            .order_by(F("last_activity").desc(nulls_last=True))
            .first()
        )
        vendor_survey_count = vendor_survey.count()
        vendor_obj = Vendor.objects.filter(id=vendor_id).first()
        for inc in Incident.objects.filter(
            status__in=[IncidentStatus.ACTIVE, IncidentStatus.REPORTED, IncidentStatus.EXTENDED_REMEDIATION]
        ):
            if inc.affected_resources:
                incident = inc.affected_resources.split(",")
                incident = [incd.strip() for incd in incident]
                if vendor_obj.name in incident:
                    incident_objs.append(inc)
        contracts: list[Contract] = model.contract_set.exclude(is_deleted=True).order_by("effective_date")
        today = timezone.now().date()
        next_30 = [today, today + timedelta(days=30)]
        next_180 = [today, today + timedelta(days=180)]
        contract_section["total"] = contracts.count()
        contract_section["next_30"] = contracts.filter(superseded_by=None, next_expiration__range=next_30).count()
        contract_section["next_180"] = contracts.filter(superseded_by=None, next_expiration__range=next_180).count()
        try:
            for data in contracts:
                child_object = contracts.filter(parent_contract=data)
                contracts = contracts.exclude(id__in=[i.id for i in child_object])
                data.childs = child_object
                if data.superseded_by:
                    contracts = get_superseded_by_ids(data.superseded_by, contracts, data)
        except Exception as e:
            print(e)
        contracts = contracts.order_by(F("superseded_by").desc(nulls_last=True))
        # Contact section details
        contacts: list[Contact] = model.contact_set.exclude(is_deleted=True)
        contact_section["total"] = contacts.count()
        latest_contact = contacts.order_by(
            Case(
                When(role=ContactRole.SALES_EXECUTIVE, then=Value(ContactRole.ACCOUNT_MANAGER)),
                When(role=ContactRole.ACCOUNT_MANAGER, then=Value(ContactRole.SALES_EXECUTIVE)),
                When(role=ContactRole.LEGAL, then=Value(ContactRole.TECHNOLOGY)),
                When(role=ContactRole.ACCOUNTING, then=Value(ContactRole.PRIMARY_BUSINESS_ADDRESS)),
                When(role=ContactRole.TECHNOLOGY, then=Value(ContactRole.ACCOUNTING)),
                When(role=ContactRole.OPERATIONS, then=Value(ContactRole.LEGAL)),
                default=Value(ContactRole.OPERATIONS),
            )
        ).first()
        contact_section["contact"] = latest_contact
        if latest_contact:
            contact_section["phone"] = latest_contact.phone_set.exclude(is_deleted=True).first()

        contract_document = Document.objects.filter(contract__in=contracts).exclude(is_deleted=True)
        documents: list[Document] = (model.document_set.exclude(is_deleted=True) | contract_document).distinct()
        document_section["total"] = documents.count()
        last_30 = [today - timedelta(days=30), today + timedelta(days=1)]
        document_section["last_30"] = (
            (documents.filter(created_at__range=last_30) or documents.filter(updated_at__range=last_30)).distinct()
        ).count()

        # Task section details
        tasks: list[tasks] = model.task_set.all()
        task_section["total"] = tasks.count()
        task_section["in_process_total"] = tasks.filter(status=TaskStatus.IN_PROCESS).count()
        task_section["hold_total"] = tasks.filter(status=TaskStatus.ON_HOLD).count()
        task_section["not_started_total"] = tasks.filter(status=TaskStatus.NOT_STARTED).count()
    if request.method == "POST":
        form = VendorForm(request.POST, model=model, instance=model)
        if form.is_valid():
            model = form.save(commit=False)
            vendor_data = Vendor.objects.filter(pk=vendor_id)
            if vendor_data:
                if not isOrgAdmin(request.user) and not model.id:
                    model.owner = request.user
                elif not isOrgAdmin(request.user):
                    model.owner = vendor_data.first().owner
            else:
                if not isOrgAdmin(request.user):
                    model.owner = request.user
            if "risk_description" in form.changed_data:
                users = get_mention_user(request.POST["risk_description"])
                if vendor_data:
                    prev_users = get_mention_user(vendor_data.first().risk_description)
                    if prev_users:
                        users = [i for i in users if i not in prev_users]
                send_mention_email(
                    users,
                    "Third Party",
                    f"{request.user.first_name} {request.user.last_name}",
                    request.POST["name"],
                    request.POST["risk_description"],
                )
            model.save()
            history = model.history.filter(pk=model.history.latest().pk).update(history_user=request.user)
            ofac_results = vendor_search(model)
            if ofac_results:
                if not model.owner:
                    form.fields["owner"].initial = request.user.pk
                else:
                    form.fields["owner"].initial = model.owner.id
                if not isOrgAdmin(request.user):
                    form.fields["owner"].disabled = True
                context = {
                    "segment": "vendors",
                    "model": model,
                    "form": form,
                    "contacts": contacts,
                    "contracts": contracts,
                    "organization": get_user_org(request.user),
                    "documents": documents,
                    "tasks": tasks,
                    "section": section,
                    "task_section": task_section,
                    "document_section": document_section,
                    "contact_section": contact_section,
                    "contract_section": contract_section,
                    "ofac_results": ofac_results,
                    "document_permission": get_document_permission(request.user, model) if model else False,
                    "edit_doc_permission": get_edit_document_permission(request.user, model) if model else False,
                    "users": org_users(request.user),
                    "org_question": org_question,
                    "vendor_survey": vendor_survey,
                    "vendor_survey_count": vendor_survey_count,
                    "incident_objs": incident_objs,
                    "open_questionnaire": open_questionnaire,
                    "last_viewed": last_viewed,
                    "org_business_process": get_vendor_process(get_user_org(request.user))
                }
                return render(request, "vendors/vendor_information.html", context)
    else:
        for contact_model in contacts:
            contact_model.preferred_phone = next(
                (phone for phone in contact_model.phone_set.exclude(is_deleted=True) if phone.is_preferred),
                contact_model.phone_set.exclude(is_deleted=True).first(),
            )
        form = VendorForm(model=model, initial=model.__dict__)
    if not model.id:
        form.fields["owner"].initial = request.user.pk
    if not isOrgAdmin(request.user):
        form.fields["owner"].disabled = True
    context = {
        "segment": "vendors",
        "model": model,
        "form": form,
        "contacts": contacts,
        "contracts": contracts,
        "organization": get_user_org(request.user),
        "documents": documents,
        "tasks": tasks,
        "section": section,
        "task_section": task_section,
        "document_section": document_section,
        "contact_section": contact_section,
        "contract_section": contract_section,
        "ofac_results": ofac_results,
        "document_permission": get_document_permission(request.user, model) if model else False,
        "edit_doc_permission": get_edit_document_permission(request.user, model) if model else False,
        "users": org_users(request.user),
        "org_question": org_question,
        "vendor_survey": vendor_survey,
        "vendor_survey_count": vendor_survey_count,
        "incident_objs": incident_objs,
        "open_questionnaire": open_questionnaire,
        "last_viewed": last_viewed,
        "org_business_process": get_vendor_process(get_user_org(request.user))
    }
    return render(request, "vendors/vendor_information.html", context)


@login_required
def contact(request, vendor_id: int, contact_id: int = None):
    """contact view"""
    ofac_results = None
    vendor_model = get_object_or_404(org_vendors(request.user), pk=vendor_id)
    contact_model = (
        vendor_model.contact_set.filter(id=contact_id).exclude(is_deleted=True).first()
        if contact_id
        else Contact(vendor=vendor_model)
    )
    if not contact_model:
        return HttpResponseNotFound()
    phones = []
    if contact_model.id:
        phones = contact_model.phone_set.exclude(is_deleted=True)
    contact_model.vendor_name = vendor_model.name
    if request.method == "POST":
        form = ContactForm(request.POST, instance=contact_model)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            ofac_results = contact_search(contact=instance)
            if ofac_results:
                context = {
                    "segment": ["vendors", "contact"],
                    "form": form,
                    "model": contact_model,
                    "phones": phones,
                    "organization": get_user_org(request.user),
                    "ofac_results": ofac_results,
                    "users": org_users(request.user),
                }
                return render(request, "vendors/contact_form.html", context)
    elif request.path.endswith("delete"):
        contact_object = Contact.objects.filter(id=contact_id, vendor_id=vendor_id)
        contact_object.update(is_deleted=True)
        url = (reverse("vendor-edit", args=[vendor_id])) + "?section=CONTACTS"
        return HttpResponseRedirect(url)
    else:
        form = ContactForm(initial=contact_model.__dict__)
    context = {
        "segment": ["vendors", "contact"],
        "form": form,
        "model": contact_model,
        "phones": phones,
        "organization": get_user_org(request.user),
        "ofac_results": ofac_results,
        "users": org_users(request.user),
    }

    return render(request, "vendors/contact_form.html", context)


@login_required
def phone(request, vendor_id: int, contact_id: int, phone_id: int = None):
    """phone view"""
    vendor_model = get_object_or_404(org_vendors(request.user), pk=vendor_id)
    contact_model = vendor_model.contact_set.filter(id=contact_id).first()
    if not contact_model:
        return HttpResponseNotFound()
    phone_model = (
        contact_model.phone_set.filter(id=phone_id).exclude(is_deleted=True).first()
        if phone_id
        else Phone(contact=contact_model)
    )
    if not phone_model:
        return HttpResponseNotFound()
    phone_model.vendor_name = vendor_model.name
    phone_model.contact_name = str(contact_model)
    phone_model.vendor_id = vendor_id

    # Handle request
    if request.method == "POST":
        form = PhoneForm(request.POST, instance=phone_model)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.save()
            return HttpResponseRedirect(reverse("contact-edit", args=[vendor_id, contact_id]))
    elif request.path.endswith("delete"):
        phone_object = Phone.objects.filter(id=phone_id, contact_id=contact_id)
        phone_object.update(is_deleted=True)
        return HttpResponseRedirect(reverse("contact-edit", args=[vendor_id, contact_id]))
    else:
        form = PhoneForm(initial=phone_model.__dict__)

    context = {
        "segment": ["vendors", "contact", "phone"],
        "form": form,
        "model": phone_model,
        "organization": get_user_org(request.user),
    }

    return render(request, "vendors/phone_form.html", context)


@login_required
def contract(request, vendor_id, contract_id=None, popup=None):
    """contract view"""
    vendor_model = get_object_or_404(org_vendors(request.user), pk=vendor_id)
    contract_model = (
        vendor_model.contract_set.prefetch_related("superseded_by")
        .filter(id=contract_id)
        .exclude(is_deleted=True)
        .first()
        if contract_id
        else Contract(vendor=vendor_model)
    )
    if not contract_model:
        return HttpResponseNotFound()
    contract_model.vendor_name = vendor_model.name
    documents = []
    if contract_model.id:
        documents: list[Document] = contract_model.document_set.exclude(is_deleted=True)
    contract_object = Contract.objects.filter(pk=contract_id)
    if request.method == "POST":
        form = ContractForm(vendor_model, data=request.POST, instance=contract_model)
        if form.is_valid():
            if "terms" in form.changed_data:
                users = get_mention_user(request.POST["terms"])
                if contract_object:
                    prev_users = get_mention_user(contract_object.first().terms)
                    if prev_users:
                        users = [i for i in users if i not in prev_users]
                send_mention_email(
                    users,
                    "Contract",
                    f"{request.user.first_name} {request.user.last_name}",
                    request.POST["title"],
                    request.POST["terms"],
                )
            instance = form.save(commit=False)
            instance.save()
            history = instance.history.filter(pk=instance.history.latest().pk).update(history_user=request.user)
            if popup:
                return JsonResponse({"contract_id": instance.pk})
            return HttpResponseRedirect(reverse("contract-edit", args=[vendor_id, instance.id]))
    elif request.path.endswith("delete"):
        contract_object = Contract.objects.filter(id=contract_id, vendor_id=vendor_id)
        contract_object.update(is_deleted=True)
        return HttpResponseRedirect(reverse("vendor-edit", args=[vendor_id]) + "?section=CONTRACTS")
    else:
        form = ContractForm(vendor_model, initial=contract_model.__dict__)

    context = {
        "segment": ["vendors", "contract"],
        "form": form,
        "model": contract_model,
        "documents": documents,
        "organization": get_user_org(request.user),
        "document_permission": get_document_permission(request.user, vendor_model) if vendor_model else False,
        "edit_doc_permission": get_edit_document_permission(request.user, vendor_model) if vendor_model else False,
        "users": org_users(request.user),
    }

    return render(request, "vendors/contract_form.html", context)


def get_top_superseded(obj):
    global super_var
    super_var = obj
    try:
        superseded_obj = Contract.objects.filter(superseded_by=obj).exclude(is_deleted=True)
        if superseded_obj:
            super_var = superseded_obj.first()
            get_top_superseded(superseded_obj.first())
        elif obj.parent_contract:
            super_var = obj.parent_contract
            get_top_superseded(obj.parent_contract)
        return
    except Exception as e:
        return


def get_tree_list(vendor_model, contract):
    backword_list = []
    upword_list = []
    back_up_list = []
    parents = contract
    contract_set = vendor_model.contract_set.exclude(is_deleted=True)
    try:

        def get_nth_parents(contract):
            parents = contract
            parent = contract.parent_contract
            if not parent:
                parent = contract_set.filter(superseded_by=contract).first()
            while parent:
                if parent.parent_contract:
                    parents = parent.parent_contract
                    parent = parent.parent_contract
                elif contract_set.filter(superseded_by=parent):
                    parent = contract_set.filter(superseded_by=parent).first()
                    if parent:
                        if parent.parent_contract:
                            parents = parent.parent_contract
                        else:
                            parents = parent
                else:
                    parent = None
            return parents

        contract = get_nth_parents(contract)

        def get_backword_list(contract):
            backword_list.append(contract.id)
            child_contract = contract_set.filter(parent_contract=contract)
            for data in child_contract:
                backword_list.append(data.id)
                get_backword_list(data)
            if contract.superseded_by:
                get_backword_list(contract.superseded_by)

        get_backword_list(contract)

        def get_upword_list(contract):
            upword_list.append(contract.id)
            seded_contract = contract_set.filter(superseded_by=contract)
            child_contract = contract_set.filter(parent_contract=contract)
            for data in child_contract:
                upword_list.append(data.id)
                child_sed = contract_set.filter(superseded_by=data)
                if child_sed:
                    get_backword_list(child_sed.first().id)
            if seded_contract:
                upword_list.append(seded_contract.first().id)
                get_upword_list(seded_contract.first())

        get_upword_list(contract)
        back_up_list = backword_list + upword_list
        return back_up_list
    except Exception as e:
        return back_up_list


def get_replaces_contracts(vendor_model, contract, contract_list):
    replaces_choices = (
        vendor_model.contract_set.filter(superseded_by=None)
        .exclude(is_deleted=True)
        .exclude(id__in=contract_list)
        .exclude(id=contract.id)
    )
    return replaces_choices


def get_replaced_by_contracts(vendor_model, contract, contract_list):
    seded_contract = vendor_model.contract_set.exclude(is_deleted=True)
    sed_list = []
    for data in seded_contract:
        if vendor_model.contract_set.exclude(is_deleted=True).filter(superseded_by=data):
            sed_list.append(data.id)
    contract_list.extend(sed_list)
    contract_choices = vendor_model.contract_set.exclude(id__in=contract_list).exclude(is_deleted=True)
    return contract_choices


def get_child_contracts(vendor_model, contract, contract_list):
    link_choices = (
        vendor_model.contract_set.filter(superseded_by=None, parent_contract=None)
        .exclude(pk=contract.id)
        .exclude(is_deleted=True)
        .exclude(parent_contract_id=contract.id)
        .annotate(children=Count("child_contracts"))
        .exclude(children__gt=0)
        .exclude(id__in=contract_list)
    )
    return link_choices


@login_required
@csrf_exempt
def contract_links(
    request, vendor_id: int, contract_id: int, child_contract_id: int = None, relation_type: str = None
):
    """view for links section of a contract"""

    # get info for referenced contract

    vendor_model = get_object_or_404(org_vendors(request.user), pk=vendor_id)
    contract_model = get_object_or_404(vendor_model.contract_set, pk=contract_id)
    child_contract = get_object_or_404(vendor_model.contract_set, pk=child_contract_id) if child_contract_id else None
    if request.method == "POST":
        if relation_type == "link":
            # add a parent to the child
            child_contract.parent_contract = contract_model
            child_contract.save()
        elif relation_type == "replaced_by":
            if child_contract:
                contract_model.superseded_by = child_contract
                contract_model.save()
        elif relation_type == "replaces":
            if child_contract:
                parent: Contract = child_contract
                parent.superseded_by = contract_model
                parent.save()
    elif request.method == "DELETE":
        if relation_type == "child":
            # remove a link
            if child_contract_id == contract_model.parent_contract_id:
                # remove a parent
                contract_model.parent_contract = None
                contract_model.save()
            else:
                # remove a child
                child_contract.parent_contract = None
                child_contract.save()
        elif relation_type == "related":
            superseded_by = vendor_model.contract_set.filter(superseded_by=child_contract)
            if superseded_by:
                superseded_by.first().superseded_by = None
                superseded_by.first().save()
            else:
                child_contract.superseded_by = None
                child_contract.save()

    # render response
    if contract_model.parent_contract:
        superseded_obj = get_top_superseded(contract_model.parent_contract)
    else:
        superseded_obj = get_top_superseded(contract_model)
    links = list(contract_model.child_contracts.all())
    if contract_model.parent_contract:
        parent = contract_model.parent_contract
        parent.is_parent = True
        links.append(parent)
        for related in vendor_model.contract_set.exclude(pk=contract_id).filter(
            parent_contract_id=contract_model.parent_contract_id
        ):
            related.is_sibling = True
            links.append(related)
    contract_list = get_tree_list(vendor_model, contract_model)
    contract_list.append(contract_id)

    self_seded = vendor_model.contract_set.filter(superseded_by=contract_model)
    if self_seded:
        contract_list.append(self_seded.first().id)
    contract_list = list(set(contract_list))
    replaces_choices = get_replaces_contracts(vendor_model, contract_model, contract_list)
    if self_seded or contract_model.parent_contract:
        replaces_choices = None

    contract_choices = get_replaced_by_contracts(vendor_model, contract_model, contract_list)
    cros_icon = False
    if contract_model.superseded_by:
        contract_choices = None
        cros_icon = True
    link_choices = get_child_contracts(vendor_model, contract_model, contract_list)
    return render(
        request,
        "vendors/contract_links.html",
        {
            "model": contract_model,
            "links": sorted(links, key=lambda x: x.title),
            "link_choices": link_choices,
            "contract_parent": super_var,
            "contract_choices": contract_choices,
            "repl_choices": replaces_choices,
            "cros_icon": cros_icon,
        },
    )


@login_required
def document(request, vendor_id, contract_id, document_id=None):
    """document view"""
    vendor_model = get_object_or_404(org_vendors(request.user), pk=vendor_id)
    contract_model = vendor_model.contract_set.filter(id=contract_id).first()
    if not contract_model:
        return HttpResponseNotFound()
    document_model = (
        contract_model.document_set.filter(id=document_id).exclude(is_deleted=True).first()
        if document_id
        else Document(contract=contract_model)
    )
    if not document_model:
        return HttpResponseNotFound()
    document_model.vendor_name = vendor_model.name
    document_model.contract_title = contract_model.title
    document_model.vendor_id = vendor_id

    if request.method == "POST":
        old_path = str(document_model.path)
        if request.FILES and "path" in request.FILES:
            document_model.name = request.FILES["path"].name
        form = DocumentForm(request.POST, request.FILES, instance=document_model)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.contract_id = contract_id
            if document_id:
                instance.updated_at = timezone.now()
            try:
                file = request.FILES["path"]
                filename, ext = os.path.splitext(os.path.basename(file.name))
                filename = f"{filename}-{uuid4()}{ext}"
            except Exception as e:
                file = instance.path
                filename = file.name.split("/")[-1]
            filename, ext = os.path.splitext(os.path.basename(file.name))
            filename = f"{filename}-{uuid4()}{ext}"
            filepath = f"{get_user_org(request.user).pk}/contracts/{contract_model.id}/{filename}"
            file_data = file.read()
            instance.path = default_storage.save(filepath, ContentFile(file_data))

            instance.save()
            if old_path:
                default_storage.delete(old_path)
            return HttpResponseRedirect(reverse("contract-edit", args=[vendor_id, contract_id]))
    elif request.path.endswith("view"):
        with default_storage.open(document_model.path.name, "rb") as file:
            mime_type, _ = mimetypes.guess_type(document_model.path.name)
            response = HttpResponse(file.read(), content_type=mime_type)
            response["Content-Disposition"] = f'inline; filename="{document_model.name}"'
            return response
    elif request.path.endswith("delete"):
        document_object = Document.objects.filter(id=document_id, contract_id=contract_id)
        document_object.update(is_deleted=True)
        return HttpResponseRedirect(reverse("contract-edit", args=[vendor_id, contract_id]))
    else:
        form = DocumentForm(initial=document_model.__dict__)
        form.fields["contract"].widget.attrs["disabled"] = True
    if not get_edit_document_permission(request.user, vendor_model):
        return HttpResponseRedirect(reverse("contract-edit", args=[vendor_id, contract_id]))
    context = {
        "segment": ["vendors", "contract", "document"],
        "form": form,
        "model": document_model,
        "organization": get_user_org(request.user),
    }

    return render(request, "vendors/document_form.html", context)


@login_required
def addition_details(request, vendor_id):
    """vendor view"""
    section = "TASK"
    section_data = request.GET.get("section", "")
    if section_data:
        section = section_data
    model = get_object_or_404(org_vendors(request.user), pk=vendor_id) if vendor_id else Vendor(org=None)
    model.org = model.org if hasattr(model, "org") else get_user_org(request.user)
    if request.method == "POST":
        vendor_object = Vendor.objects.filter(pk=vendor_id)
        if request.POST["notes"] != vendor_object.first().notes:
            users = get_mention_user(request.POST["notes"])
            prev_users = get_mention_user(vendor_object.first().notes)
            if prev_users:
                users = [i for i in users if i not in prev_users]
            send_mention_email(
                users,
                "Third Party",
                f"{request.user.first_name} {request.user.last_name}",
                vendor_object.first().name,
                request.POST["notes"],
            )
        vendor_object.update(
            twitter=request.POST["twitter"],
            website=request.POST["website"],
            linkedin=request.POST["linkedin"],
            facebook=request.POST["facebook"],
            stock_symbol=request.POST["stock_symbol"],
            notes=request.POST["notes"],
        )
        vendor_object.first().save()
        history = model.history.filter(pk=model.history.latest().pk).update(history_user=request.user)
        return HttpResponseRedirect(reverse("vendor-edit", args=[model.id]) + "?section=" + section)
    else:
        form = VendorForm(model=model, initial=model.__dict__)

    context = {
        "segment": ["vendors", "additional details"],
        "form": form,
        "model": model,
        "organization": get_user_org(request.user),
        "section": section,
        "users": org_users(request.user),
    }

    return render(request, "vendors/vendor_additional_details.html", context)


@login_required
def documents(request, vendor_id, document_id=None, popup=None):
    """document view"""
    vendor_model = get_object_or_404(org_vendors(request.user), pk=vendor_id)
    document_model = (
        Document.objects.filter(id=document_id).exclude(is_deleted=True).first()
        if document_id
        else Document(vendor=vendor_model)
    )
    if not document_model:
        return HttpResponseNotFound()
    document_model.vendor_name = vendor_model.name
    document_model.vendor_id = vendor_id

    if request.method == "POST":
        old_path = str(document_model.path)
        if request.FILES and "path" in request.FILES:
            document_model.name = request.FILES["path"].name
        form = DocumentForm(request.POST, request.FILES, instance=document_model)

        if form.is_valid():
            instance = form.save(commit=False)
            if document_id:
                instance.updated_at = timezone.now()
            try:
                file = request.FILES["path"]
                filename, ext = os.path.splitext(os.path.basename(file.name))
                filename = f"{filename}-{uuid4()}{ext}"
            except Exception as e:
                file = instance.path
                filename = file.name.split("/")[-1]
            if request.POST["contract"]:
                filepath = f"{get_user_org(request.user).pk}/contracts/{request.POST['contract']}/{filename}"
            else:
                filepath = f"{get_user_org(request.user).pk}/vendors/{vendor_id}/{filename}"
            file_data = file.read()
            instance.path = default_storage.save(filepath, ContentFile(file_data))

            instance.save()
            if old_path:
                default_storage.delete(old_path)
            if popup == "dashboard_page":
                return HttpResponseRedirect(reverse("dashboard"))
            elif popup == "vendor_page":
                return HttpResponseRedirect(reverse("vendors"))
            elif popup == "contract_index":
                return HttpResponseRedirect(reverse("contract_index"))
            return HttpResponseRedirect(reverse("vendor-edit", args=[vendor_id]) + "?section=DOCUMENTS")
    elif request.path.endswith("view"):
        with default_storage.open(document_model.path.name, "rb") as file:
            mime_type, _ = mimetypes.guess_type(document_model.path.name)
            response = HttpResponse(file.read(), content_type=mime_type)
            response["Content-Disposition"] = f'inline; filename="{document_model.name}"'
            return response
    elif request.path.endswith("delete"):
        document_object = Document.objects.filter(id=document_id, vendor_id=vendor_id)
        document_object.update(is_deleted=True)
        return HttpResponseRedirect(reverse("vendor-edit", args=[vendor_id]) + "?section=DOCUMENTS")
    else:
        form = DocumentForm(initial=document_model.__dict__)
        form.fields["contract"].queryset = vendor_model.contract_set.all()
    if not get_edit_document_permission(request.user, vendor_model):
        return HttpResponseRedirect(reverse("vendor-edit", args=[vendor_id]) + "?section=DOCUMENTS")
    context = {
        "segment": ["vendors", "document"],
        "form": form,
        "model": document_model,
        "organization": get_user_org(request.user),
    }
    if popup == "dashboard_page":
        return HttpResponseRedirect(reverse("dashboard"))
    elif popup == "vendor_page":
        return HttpResponseRedirect(reverse("vendors"))
    elif popup == "contract_index":
        return HttpResponseRedirect(reverse("contract_index"))
    return render(request, "vendors/documents_form.html", context)


def generate_excel(request, file_name, columns_list, data_list, file_type):
    empty_row = [None] * len(columns_list)
    if len(data_list) == 1:
        data_list.append(empty_row)
    elif len(data_list) == 0:
        data_list.extend([empty_row, empty_row])
    pd.options.mode.chained_assignment = None
    df = pd.DataFrame(data_list, columns=columns_list)
    writer = pd.ExcelWriter(file_name, engine="xlsxwriter")
    df.to_excel(writer, sheet_name="Sheet1", startrow=0, index=False)
    workbook = writer.book
    worksheet = writer.sheets["Sheet1"]
    header_format = workbook.add_format(
        {
            "bold": True,
            "valign": "top",
            "border": 2,
            "top": 0,
            "right": 0,
            "left": 0,
        }
    )
    removed_header = workbook.add_format(
        {
            "bold": False,
            "valign": "top",
            "border": 0,
        }
    )
    cell_format_color = workbook.add_format(
        {"bold": True, "valign": "top", "bg_color": "#D3D3D3", "border": 2, "top": 0, "left": 0, "bottom": 0}
    )
    cell_format_border = workbook.add_format(
        {
            "bold": True,
            "valign": "top",
            "bg_color": "#D3D3D3",
            "border": 2,
            "top": 0,
            "left": 0,
        }
    )
    for col_num, value in enumerate(df.columns.values):
        if col_num not in [0, 1]:
            worksheet.write(0, col_num, value, header_format)
        else:
            if col_num == 1:
                worksheet.write(0, col_num, value, removed_header)
    worksheet.write(0, 0, file_type, cell_format_color)
    name = get_user_org(request.user).name
    worksheet.write(1, 0, name, cell_format_color)
    tz = pytz.timezone("US/Pacific")
    worksheet.write(2, 0, f"Generated {datetime.now(tz).strftime('%m/%d/%Y %H:%M')}", cell_format_border)
    writer.save()

    with open(file_name, "rb") as file:
        response = HttpResponse(
            file.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = "attachment; filename=%s" % f"{file_type}-{get_user_org(request.user)}.xlsx"
    return response


def get_contact_list(data):
    contact_object = data.contact_set.exclude(is_deleted=True).order_by(
        Case(
            When(role=1, then=Value(2)),
            When(role=2, then=Value(1)),
            When(role=3, then=Value(5)),
            When(role=4, then=Value(7)),
            When(role=5, then=Value(4)),
            When(role=6, then=Value(3)),
            default=Value(6),
        )
    )
    contact_list = [None] * 8
    if contact_object:
        contact_list[0] = f"{contact_object[0].first_name} {contact_object[0].last_name}"
        contact_list[1] = contact_object[0].get_role_display()
        contact_list[2] = contact_object[0].email
        contact_list[3] = contact_object[0].phone_set.exclude(is_deleted=True).first()
    if len(contact_object) >= 2:
        contact_list[4] = f"{contact_object[1].first_name} {contact_object[1].last_name}"
        contact_list[5] = contact_object[1].get_role_display()
        contact_list[6] = contact_object[1].email
        contact_list[7] = contact_object[1].phone_set.exclude(is_deleted=True).first()
    return contact_list


@login_required
def reports(request):
    if request.path.endswith("critical-third-parties"):
        file_name = f"critical-third-parties-{get_user_org(request.user)}.xlsx"
        vendor_object = org_vendors(request.user).filter(critical=True).order_by("name")
        data_list = []
        file_type = "Critical Third Parties"
        columns_list = [
            file_type,
            "",
            "Name",
            "Relationship Manager",
            "Status",
            "Inherent Risk",
            "Residual Risk",
            "Category",
            "Business Process",
        ]
        for data in vendor_object:
            owner_name = f"{data.owner.first_name} {data.owner.last_name}" if data.owner else None
            data_list.append(
                [
                    None,
                    None,
                    data.name,
                    owner_name,
                    VENDOR_STATUS_DISPLAYNAMES[data.status] if data.status else None,
                    RISK_GRADE_DISPLAYNAMES[data.inherent_risk],
                    RISK_GRADE_DISPLAYNAMES[data.residual_risk],
                    data.category,
                    data.org_business_process,
                ]
            )
        return generate_excel(request, file_name, columns_list, data_list, file_type)
    elif request.path.endswith("third-party-directory"):
        file_name = f"Third-Party-Directory-{get_user_org(request.user)}.xlsx"
        vendor_object = org_vendors(request.user).order_by("name")
        data_list = []
        file_type = "Third Party Directory"
        columns_list = [
            file_type,
            "",
            "Name",
            "Status",
            "Offshore",
            "Critical",
            "Category",
            "Relationship Owner",
            "Contact",
            "Type",
            "Email",
            "Phone",
            "Contact",
            "Type",
            "Email",
            "Phone",
        ]
        for data in vendor_object:
            owner_name = f"{data.owner.first_name} {data.owner.last_name}" if data.owner else None
            data_list.append(
                [
                    None,
                    None,
                    data.name,
                    VENDOR_STATUS_DISPLAYNAMES[data.status] if data.status else None,
                    TRUE_FALSE_CHOICES[data.is_offshore][1],
                    TRUE_FALSE_CHOICES[data.critical][1],
                    data.category,
                    owner_name,
                ]
                + get_contact_list(data)
            )
        return generate_excel(request, file_name, columns_list, data_list, file_type)
    elif request.path.endswith("task-reports"):
        from apps.tasks.views import get_priority, get_status, org_tasks

        file_name = f"Tasks-By-Owner-{get_user_org(request.user)}.xlsx"
        vendor_object = org_tasks(request.user).order_by("owner", "linked_resources")
        data_list = []
        file_type = "Task By Owner"
        columns_list = [
            file_type,
            "",
            "Owner",
            "Third Party Name",
            "Task Title",
            "Created Date",
            "Closed Date",
            "Priority",
            "Status",
            "Resources",
        ]
        for data in vendor_object:
            closed_date = data.closed_date.date().strftime("%m/%d/%Y") if data.closed_date else None
            data_list.append(
                [
                    None,
                    None,
                    data.owner,
                    data.linked_resources,
                    data.title,
                    data.created_at.date().strftime("%m/%d/%Y"),
                    closed_date,
                    get_priority(data.priority),
                    get_status(data.status),
                    data.linked_resources,
                ]
            )
        return generate_excel(request, file_name, columns_list, data_list, file_type)
    elif request.path.endswith("incidents-reports"):
        from apps.incidents.views import org_incidents

        file_name = f"Incidents-By-Owner-{get_user_org(request.user)}.xlsx"
        vendor_object = org_incidents(request.user).order_by("start_date")
        data_list = []
        file_type = "Incidents By Owner"
        columns_list = [file_type, "", "Title", "Resources", "Severity", "Start Date", "End Date", "Status"]
        for data in vendor_object:
            data_list.append(
                [
                    None,
                    None,
                    data.title,
                    data.affected_resources,
                    SEVERITY_DISPLAYNAMES[data.severity],
                    data.start_date.date().strftime("%m/%d/%Y") if data.start_date else None,
                    data.end_date.date().strftime("%m/%d/%Y") if data.end_date else None,
                    INCIDENT_STATUS_DISPLAYNAMES[data.status],
                ]
            )
        return generate_excel(request, file_name, columns_list, data_list, file_type)
    elif request.path.endswith("expiring-contracts-reports"):
        file_name = f"Expiring-Contracts-{get_user_org(request.user)}.xlsx"
        expiry_date = timezone.now().date() + timedelta(days=180)
        contract_object = (
            Contract.objects.filter(
                next_expiration__lte=expiry_date, superseded_by=None, vendor__org=get_user_org(request.user)
            )
            .exclude(is_deleted=True)
            .order_by("vendor", "title")
        )
        data_list = []
        file_type = "Expiring Contracts"
        columns_list = [
            file_type,
            "",
            "Third Party Name",
            "Contract Title",
            "Effective Date",
            "Next Expiration",
            "Auto Renews",
            "Parent Contract Title",
            "Relationship Owner",
        ]
        for data in contract_object:
            next_expiration = data.next_expiration.strftime("%m/%d/%Y") if data.next_expiration else None
            effective_date = data.effective_date.strftime("%m/%d/%Y") if data.effective_date else None
            data_list.append(
                [
                    None,
                    None,
                    data.vendor,
                    data.title,
                    effective_date,
                    next_expiration,
                    TRUE_FALSE_CHOICES[data.is_auto_renew][1],
                    data.parent_contract,
                    data.vendor.owner,
                ]
            )
        return generate_excel(request, file_name, columns_list, data_list, file_type)
    elif request.path.endswith("risk-reports"):
        from apps.risks.views import org_risks

        file_name = f"Risk-{get_user_org(request.user)}.xlsx"
        risk_object = org_risks(request.user)
        data_list = []
        file_type = "Risk"
        columns_list = [
            file_type,
            "",
            "Risk Title",
            "Mitigation",
            "Impact",
            "Priority",
            "Likelihood",
            "Rating",
            "Category",
            "Notes",
        ]
        for data in risk_object:
            data_list.append(
                [
                    None,
                    None,
                    data.title,
                    data.mitigation,
                    data.impact,
                    data.get_priority_display(),
                    data.likelihood,
                    f"{data.get_rating} ({data.rating})",
                    data.category,
                    (data.notes.strip())[:512],
                ]
            )
        return generate_excel(request, file_name, columns_list, data_list, file_type)
    elif request.path.endswith("renew-contracts-reports"):
        file_name = f"Expiring-Contracts-{get_user_org(request.user)}.xlsx"
        contract_object = (
            Contract.objects.filter(vendor__org=get_user_org(request.user))
            .filter(Q(has_minimum_fees=True) | Q(is_auto_renew=True))
            .exclude(is_deleted=True)
            .order_by("vendor", "title")
        )
        data_list = []
        file_type = "Minimums and Auto-Renewals"
        columns_list = [
            file_type,
            "",
            "Third Party Name",
            "Contract Title",
            "Third Party Status",
            "Expiration Date",
            "Renewal Period",
            "Relationship Owner",
            "Has Minimum",
            "Auto Renews",
        ]
        for data in contract_object:
            next_expiration = data.next_expiration.strftime("%m/%d/%Y") if data.next_expiration else None
            data_list.append(
                [
                    None,
                    None,
                    data.vendor,
                    data.title,
                    data.vendor.get_status_display(),
                    next_expiration,
                    data.renewal_period_days,
                    data.vendor.owner,
                    TRUE_FALSE_CHOICES[data.has_minimum_fees][1],
                    TRUE_FALSE_CHOICES[data.is_auto_renew][1],
                ]
            )
        return generate_excel(request, file_name, columns_list, data_list, file_type)

    context = {
        "segment": "dashboard",
        "organization": get_user_org(request.user),
    }
    return render(request, "vendors/reports.html", context)


@login_required(login_url="/login/")
def ofac_searched_task(request, contact_id=None, vendor_id=None):
    from apps.administrator.models import OFACSDNResult

    if contact_id:
        contact = Contact.objects.filter(pk=contact_id).first()
        contact_report(contact_id)
        return HttpResponseRedirect(reverse("contact-edit", args=[contact.vendor.id, contact_id]))
    if vendor_id:
        vendor_report(vendor_id)
        section = "TASK"
        section_data = request.GET.get("section", "")
        if section_data:
            section = section_data
        return HttpResponseRedirect(reverse("vendor-edit", args=[vendor_id]) + "?section=" + section)


@login_required(login_url="/login/")
def ignore_ofac_task(request, contact_id=None, vendor_id=None):
    if contact_id:
        contact = Contact.objects.filter(pk=contact_id)
        contact.update(ignore_sdn=True)
        return HttpResponseRedirect(reverse("contact-edit", args=[contact.first().vendor.id, contact_id]))
    if vendor_id:
        vendor = Vendor.objects.filter(pk=vendor_id)
        vendor.update(ignore_sdn=True)
        section = "TASK"
        section_data = request.GET.get("section", "")
        if section_data:
            section = section_data
        return HttpResponseRedirect(reverse("vendor-edit", args=[vendor_id]) + "?section=" + section)


@login_required(login_url="/login/")
def ignore_ofac_result(request, vendor_id: int, contact_id: int = None):
    if contact_id:
        contact = Contact.objects.filter(pk=contact_id)
        contact.update(ignore_sdn=True)
        return HttpResponseRedirect(reverse("contact-edit", args=[contact.first().vendor.id, contact_id]))

    if vendor_id:
        vendor = Vendor.objects.filter(pk=vendor_id)
        vendor.update(ignore_sdn=True)
        section = "TASK"
        section_data = request.GET.get("section", "")
        if section_data:
            section = section_data
        return HttpResponseRedirect(reverse("vendor-edit", args=[vendor_id]) + "?section=" + section)


@login_required(login_url="/login/")
def create_ofac_result_task(request, vendor_id: int, contact_id: int = None):
    if contact_id:
        contact = Contact.objects.filter(pk=contact_id).first()
        contact_report(contact_id)
        return HttpResponseRedirect(reverse("contact-edit", args=[contact.vendor.id, contact_id]))
    if vendor_id:
        vendor_report(vendor_id)
        section = "TASK"
        section_data = request.GET.get("section", "")
        if section_data:
            section = section_data
        return HttpResponseRedirect(reverse("vendor-edit", args=[vendor_id]) + "?section=" + section)


@login_required(login_url="/login/")
def import_questionnaire(request, vendor_id: int):
    if request.method == "POST":
        import_list = list(request.POST["import_list"].split(","))
        import_list = list(set(import_list))
        for i in import_list:
            survey = OrgSurvey.objects.filter(id=i)
            header = ""
            if survey:
                vendor_survey = VendorSurvey.objects.create(
                    vendor_id=vendor_id,
                    survey=survey.first(),
                    name=survey.first().name,
                    description=survey.first().description,
                    active=survey.first().active,
                    org_version=survey.first().org_version,
                    gracen_version=survey.first().gracen_version,
                    user=request.user,
                    status=SurveyStatus.NOT_SENT,
                )
                questions = OrgQuestion.objects.filter(survey=survey.first()).order_by("ordering")
                for q in questions:
                    prev_header = header
                    header = q.header
                    if header != prev_header:
                        QuestionHeader.objects.create(name=header)
                    vendor_question = VendorSurveyQuestion.objects.create(
                        vendor_id=vendor_id,
                        survey_id=vendor_survey.id,
                        label=q.label,
                        type_field=q.type_field,
                        choices=q.choices,
                        help_text=q.help_text,
                        required=q.required,
                        ordering=q.ordering,
                        header=q.header,
                    )
                    vendor_question.key = f"{get_user_org(request.user).pk}-{vendor_survey.pk}-{vendor_question.pk}"
                    vendor_question.save()
        return HttpResponseRedirect(reverse("vendor-edit", args=[vendor_id]) + "?section=QUESTIONS")


@login_required(login_url="/login/")
def send_to_vendor(request, survey_id):
    if request.method == "POST":
        survey = OrgSurvey.objects.filter(id=survey_id)
        vendor_id = request.POST.get("send_to", None)
        if vendor_id == "":
            vendor_id = None
        due_date = request.POST.get("due_date", None)
        vendor = Vendor.objects.filter(id=vendor_id)
        header = ""
        if vendor.exists() and survey.exists():
            vendor_survey = VendorSurvey.objects.create(
                vendor_id=vendor_id,
                survey=survey.first(),
                user=request.user,
                name=survey.first().name,
                description=survey.first().description,
                active=survey.first().active,
                is_sent_by_org=True,
                due_date=due_date if due_date != "" else None,
                org_version=survey.first().org_version,
                gracen_version=survey.first().gracen_version,
                status=SurveyStatus.NOT_SENT,
            )
            questions = OrgQuestion.objects.filter(survey=survey.first()).order_by("ordering")
            for q in questions:
                prev_header = header
                header = q.header
                if header != prev_header:
                    QuestionHeader.objects.create(name=header)
                vendor_question = VendorSurveyQuestion.objects.create(
                    vendor_id=vendor_id,
                    survey_id=vendor_survey.id,
                    label=q.label,
                    type_field=q.type_field,
                    choices=q.choices,
                    help_text=q.help_text,
                    required=q.required,
                    ordering=q.ordering,
                    header=q.header,
                )
                vendor_question.key = f"{get_user_org(request.user).pk}-{vendor_survey.pk}-{vendor_question.pk}"
                vendor_question.save()
        return JsonResponse({})


@login_required(login_url="/login/")
def vendor_surveys(request, vendor_id):
    search = request.GET.get("q", None)
    vendor_survey = VendorSurvey.objects.filter(vendor_id=vendor_id, active=True, is_sent_by_org=True)
    if search:
        vendor_survey = vendor_survey.filter(name__icontains=search)
    for survey in vendor_survey:
        answer = VendorSurveyUserAnswer.objects.filter(vendor_id=vendor_id, survey=survey)
        if answer.exists():
            survey.answer = answer.first()
        else:
            survey.answer = None
    context = {
        "vendor": Vendor.objects.filter(id=vendor_id).first(),
        "surveys": vendor_survey,
    }
    return render(request, "vendors/survey_index.html", context)


def contract_index(request):
    sort = request.GET.get("sort", "vendor__name")
    page = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 15)
    filter_by = request.GET.get("filter_by", None)
    param = request.GET.get("param", None)
    search = request.GET.get("search", "")
    contracts = (
        Contract.objects.filter(vendor__org=get_user_org(request.user))
        .exclude(is_deleted=True)
        .order_by("vendor__name", "title")
    )
    contract_activity = get_contract_activity(request.user)
    has_minimums = contracts.filter(has_minimum_fees=True)
    auto_renews = contracts.filter(is_auto_renew=True)
    if param:
        if filter_by == "third_party":
            contracts = contracts.filter(vendor_id=param)
        elif filter_by == "contract":
            if param == "has_minimums":
                contracts = has_minimums
            elif param == "auto_renews":
                contracts = auto_renews
            else:
                contracts = get_contract_activity(request.user, search)[param]
        elif filter_by == "owner":
            contracts = contracts.filter(vendor__owner_id=param).distinct()
    if search:
        contracts = contracts.filter(Q(title__icontains=search) | Q(vendor__name__icontains=search))
    contracts = contracts.distinct()
    total_data = contracts.count()
    new_page_size = page_size
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
    table = ContractTable(data=contracts, order_by=sort, template_name="table/custome_table.html")
    table.paginate(page=page, per_page=page_size)

    tree_contracts = contracts
    search_list = []
    if new_page_size != "All":
        total_contract = contracts.count()
        total_pages = math.ceil((total_contract / int(page_size)))
        page_numbers = [i for i in range(1, total_pages + 1)]
    try:
        for data in tree_contracts:
            child_object = tree_contracts.filter(parent_contract=data)
            tree_contracts = tree_contracts.exclude(id__in=[i.id for i in child_object])
            if search or filter_by == "contract":
                get_top_superseded(data)
                search_list.append(super_var)
            else:
                if data.superseded_by:
                    tree_contracts = get_superseded_by_ids(data.superseded_by, tree_contracts, data)
    except Exception as e:
        print(e)
    tree_contracts = tree_contracts.distinct()
    if search or filter_by == "contract":
        tree_contracts = (
            Contract.objects.filter(
                vendor__org=get_user_org(request.user), id__in=[i.id for i in list(set(search_list))]
            )
            .exclude(is_deleted=True)
            .order_by("vendor__name", "title")
        ).distinct()

    if new_page_size != "All":
        page = int(page)
        page_size = int(new_page_size)
        page_capacity = page * int(page_size)
        page_ids = []
        total_node_count = 0
        page_count = 1
        page_nodes = 0
        for vendor in tree_contracts:
            # count all nodes
            nodes_count = len(set(get_tree_list(vendor.vendor, vendor)))
            total_node_count += nodes_count
            page_nodes += nodes_count
            flag = False
            if page_nodes >= 1 * page_size:
                if (page_nodes - nodes_count) < 1 * page_size:
                    if ((page_nodes - (1 * page_size)) <= 5 and nodes_count > 1) or (page_nodes == 1 * page_size):
                        page_ids.append(vendor.id)
                    else:
                        flag = True
                else:
                    flag = True
                if flag:
                    page_count += 1
                    page_nodes = nodes_count
                    new_page = True
                    if page == page_count:
                        page_ids = [vendor.id]
                    if page_count > page:
                        break
                    page_ids = [vendor.id]
            else:
                page_ids.append(vendor.id)
        next = True
        prev = True
        if len(page_numbers) > 0:
            if page == page_numbers[-1]:
                next = False
            if page == page_numbers[0]:
                prev = False
        else:
            next = False
            prev = False
        next_page = page
        prev_page = page
        if page > 0:
            next_page = page + 1
            prev_page = page - 1
        context = {
            "page_numbers": page_numbers,
            "prev": prev,
            "next": next,
            "next_page": next_page,
            "prev_page": prev_page,
            "page": page,
        }
    else:
        page_ids = []
        context = {}
    if page_ids:
        tree_contracts = tree_contracts.filter(id__in=page_ids).order_by("vendor__name", "title")
    vendor_list = org_vendors(request.user)
    document_form = DocumentForm()
    cont_document_form = DocumentForm()
    cont_document_form.fields["path"].widget.attrs["id"] = "id_path_contract_index"
    popup_contract_from = ContractForm()
    context.update(
        {
            "segment": "contracts",
            "contracts": tree_contracts,
            "organization": get_user_org(request.user),
            "users": org_users(request.user),
            "contract_activity": contract_activity,
            "vendor_owners": org_vendors(request.user).exclude(owner=None).order_by("owner").distinct("owner"),
            "vendors": org_vendors(request.user).order_by("name").distinct("name"),
            "has_minimums": has_minimums,
            "auto_renews": auto_renews,
            "tabledata": table,
            "document_form": document_form,
            "popup_contract_from": popup_contract_from,
            "vendor_list": vendor_list,
            "cont_document_form": cont_document_form,
        }
    )
    return render(request, "vendors/contract_index.html", context)


@login_required(login_url="/login/")
def get_vendor_contract(request, vendor_id):
    contract_object = Contract.objects.filter(vendor_id=vendor_id).exclude(is_deleted=True).values("title", "id")
    return JsonResponse(list(contract_object), safe=False)


@login_required(login_url="/login/")
def send_survey_to_vendor(request, vendor_id, survey_id):
    if request.method == "POST":
        tz = pytz.timezone("US/Pacific")
        reciever = Contact.objects.filter(id=request.POST["user_id"]).first()
        if not reciever:
            return HttpResponseRedirect(reverse("vendor-edit", args=[vendor_id]) + "?section=QUESTIONS")
        if not reciever.email:
            return HttpResponseRedirect(reverse("vendor-edit", args=[vendor_id]) + "?section=QUESTIONS")
        vendor = Vendor.objects.filter(id=vendor_id)
        survey = VendorSurvey.objects.filter(id=survey_id)
        if not survey.first().is_sent_by_vendor:
            survey.update(
                is_sent_by_vendor=True, sent_date=datetime.now(tz), sent_by=request.user, status=SurveyStatus.SENT
            )
        if request.POST["invite_due_date"] and request.POST["invite_due_date"] != "":
            survey.update(invite_due_date=request.POST.get("invite_due_date", None))
        token = SurveyToken(vendor=vendor.first(), org=vendor.first().org, survey=survey.first(), key=uuid7str())
        token.save()
        number = random.randint(1000, 9999)
        random_str = "".join(random.choices(string.ascii_lowercase + string.ascii_uppercase, k=4))
        password = str(number) + random_str
        user = User.objects.create(
            email=str(token.key) + "_gracen@gmail.com", password=make_password(password),
            is_invited=True, first_name=reciever.first_name, last_name=reciever.last_name
        )
        sender_org = get_user_org(request.user)
        OrganizationUser.objects.create(organization=sender_org, user=user)
        token.user = user
        token.save()
        domain = request.build_absolute_uri("/")[:-1]
        url = domain + reverse("survey-login", args=[token.key])
        send_survey_link(survey.first().name, request.user.id, reciever.pk, sender_org.name, url)
        send_survey_password(survey.first().name, request.user.id, reciever.pk, sender_org.name, password)
        return HttpResponseRedirect(reverse("vendor-edit", args=[vendor_id]) + "?section=QUESTIONS")
