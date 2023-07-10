import math
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AbstractUser
from django.db.models import QuerySet
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.template import loader
from django.urls import reverse
from organizations.models import Organization, OrganizationUser

from apps.authentication.models import User
from apps.risks.tables import RiskTable
from apps.tasks.models import Task
from apps.utility.EmailServices import send_mention_email
from apps.utility.VendorUtilities import get_mention_user, org_users
from apps.vendor.views import get_user_org

from .forms import RiskForm
from .models import Risk, RiskAuditHistory

# # Create your views here.


def get_priority(value):
    value = int(value)
    if value == 1:
        return "Low"
    elif value == 2:
        return "Medium"
    elif value == 3:
        return "High"
    else:
        return "Critical"


def get_risk_rating_value(data):
    """get all unique risk rating"""
    result = []
    if data.filter(rating__lte=5):
        result.append("Low")
    if data.filter(rating__gte=6, rating__lte=11):
        result.append("Medium")
    if data.filter(rating__gte=12, rating__lte=25):
        result.append("High")
    return result


def org_risks(user: AbstractUser) -> QuerySet:
    """get all risk associated to user's org"""
    # If the user is None, has no ID or is not active
    # return an empty queryset
    if not user or not user.id or not user.is_active:
        return Risk.objects.none()

    # find only orgs that the user is associated to and that
    # are active
    org_user = OrganizationUser.objects.filter(user=user).first()
    orgs = []
    if org_user:
        orgs = [
            o.organization
            for o in OrganizationUser.objects.filter(user_id=user.id).select_related("organization")
            if o.organization.is_active
        ]
    risk = Risk.objects.filter(org__in=orgs)
    return risk


@login_required
def risks(request):
    """risk view"""
    sort = request.GET.get("sort", "title")
    page = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 15)
    search = request.GET.get("search", "")
    rating = request.GET.get("rating", None)
    search_mine = request.GET.get("self", None)

    data = org_risks(request.user)
    risk_value = get_risk_rating_value(data)
    if search:
        data = data.filter(title__icontains=search)
    if search_mine == "True":
        data = data.filter(owner=request.user)
    if rating:
        if rating == "Low":
            data = data.filter(rating__lte=5)
        elif rating == "Medium":
            data = data.filter(rating__gte=6, rating__lte=11).distinct()
        else:
            data = data.filter(rating__gte=12, rating__lte=25).distinct()

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
    table = RiskTable(data=data, order_by=sort, template_name="table/custome_table.html")
    table.paginate(page=page, per_page=page_size)

    context = {
        "segment": "risks",
        "tabledata": table,
        "search": search,
        "organization": get_user_org(request.user),
        "organization_pk": get_user_org(request.user).id if get_user_org(request.user) else "",
        "rating": risk_value,
    }
    return HttpResponse(loader.get_template("risks/index.html").render(context, request))


@login_required
def risk_view(request, risk_id: int = None):
    """risk view"""
    model = get_object_or_404(org_risks(request.user), pk=risk_id) if risk_id else Risk(org=None)
    tasks = []
    if model.id:
        tasks: list[Task] = model.task_set.exclude(is_deleted=True)
    audit_history: list[RiskAuditHistory] = RiskAuditHistory.objects.filter(risk_id=risk_id)
    model.org = model.org if hasattr(model, "org") else get_user_org(request.user)
    created_at = str(model.created_at) if risk_id else None
    if request.method == "POST":
        _mutable = request.POST._mutable
        request.POST._mutable = True
        request.POST["rating"] = int(request.POST["likelihood"]) * int(request.POST["impact"])
        request.POST._mutable = _mutable
        if risk_id:
            risk_object = Risk.objects.get(pk=risk_id)
            model_field = risk_object.__dict__
        form = RiskForm(request.POST, model=model, instance=model)
        if form.is_valid():
            if "notes" in form.changed_data:
                users = get_mention_user(request.POST["notes"])
                if risk_id:
                    prev_users = get_mention_user(risk_object.notes)
                    if prev_users:
                        users = [i for i in users if i not in prev_users]
                send_mention_email(
                    users,
                    "Risk",
                    f"{request.user.first_name} {request.user.last_name}",
                    request.POST["title"],
                    request.POST["notes"],
                )
            model = form.save(commit=False)
            model.save()
            history = model.history.filter(pk=model.history.latest().pk).update(history_user=request.user)
            return HttpResponseRedirect(reverse("risks"))
    else:
        form = RiskForm(model=model, initial=model.__dict__)
        form.fields["rating"].widget.attrs["disabled"] = True
    context = {
        "segment": "risks",
        "form": form,
        "model": model,
        "organization": get_user_org(request.user),
        "audit_history": audit_history,
        "tasks": tasks,
        "users": org_users(request.user),
    }

    return render(request, "risks/risk_form.html", context)
