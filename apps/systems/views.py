from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.models import AbstractUser
from django.db.models import Q, QuerySet
from django.template import loader
from django.urls import reverse

from organizations.models import OrganizationUser, Organization
from .tables import SystemTable
from .models import System
from .forms import SystemForm
from apps.incidents.views import get_resource_option_list_vendor, get_resource_option_list_vendor_process
import math

# Create your views here.

def org_systems(user: AbstractUser) -> QuerySet:
    """get all task associated to user's org"""
    # If the user is None, has no ID or is not active
    # return an empty queryset
    if not user or not user.id or not user.is_active:
        return System.objects.none()

    # find only orgs that the user is associated to and that
    # are active
    orgs = [
        o.organization
        for o in OrganizationUser.objects.filter(user_id=user.id).select_related("organization")
        if o.organization.is_active
    ]
    systems = System.objects.filter(org__in=orgs)
    return systems


def get_system_type(data):
    """get all unique system_type"""
    data = data.values_list("system_type", flat=True)
    unique = set(data)
    result = list(unique)
    result.sort()
    return result


def get_vendors(data):
    """get all unique vendor"""
    data = data.values_list("vendor", flat=True)
    unique = set(data)
    result = list(unique)
    # result.sort()
    return result


def get_user_org(user: AbstractUser) -> Organization:
    """get first org user is associated to"""
    if not user or not user.id or not user.is_active:
        return None

    orguser = OrganizationUser.objects.select_related("organization").filter(user=user).first()
    return orguser.organization if orguser else None


@login_required
def systems(request):
    "Systems view"
    sort = request.GET.get("sort", "name")
    page = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 15)
    filter_by = request.GET.get("filter_by", None)
    param = request.GET.get("param", None)

    data = org_systems(request.user)
    system_type = get_system_type(data)
    vendors = get_vendors(data)

    if param:
        if filter_by == "type":
            data = data.filter(system_type=param)
        elif filter_by == "vendor":
            if param == "None":
                data = data.filter(vendor__isnull=True)
            else:
                data = data.filter(vendor__contains=param)

    table = SystemTable(data=data, order_by=sort)
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
    table = SystemTable(data=data, order_by=sort, template_name="table/custome_table.html")
    table.paginate(page=page, per_page=page_size)

    context = {
        "segment": "systems",
        "tabledata": table,
        "organization": get_user_org(request.user),
        "organization_pk": get_user_org(request.user).id if get_user_org(request.user) else "",
        "system_type": system_type,
        "vendors": vendors,
    }
    return HttpResponse(loader.get_template("systems/index.html").render(context, request))


@login_required
def system(request, system_id=None):
    "System create view"

    section = "System"

    model = get_object_or_404(org_systems(request.user), pk=system_id) if system_id else System(org=None)
    model.org = model.org if hasattr(model, "org") else get_user_org(request.user)


    if request.method == "POST":
        form = SystemForm(request.POST, model=model, instance=model)
        if form.is_valid():
            model = form.save(commit=False)
            model.save()
            return HttpResponseRedirect(reverse("systems"))

    else:
        form = SystemForm(model=model, initial=model.__dict__)

    context = {
        "segment": "systems",
        "model": model,
        "form": form,
        "organization": get_user_org(request.user),
        "section": section,
        "resource_option_vendor": get_resource_option_list_vendor(request.user),
        "resource_option_process": get_resource_option_list_vendor_process(request.user),
    }
    return render(request, "systems/system_form.html", context)