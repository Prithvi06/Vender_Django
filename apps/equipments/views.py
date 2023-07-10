from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.models import AbstractUser
from django.db.models import Q, QuerySet
from django.template import loader
from django.urls import reverse

from organizations.models import OrganizationUser, Organization
from .tables import EquipmentTable
from .models import Equipment
from .forms import EquipmentForm
from apps.incidents.views import get_resource_option_list_vendor, get_resource_option_list_vendor_process
import math

# Create your views here.

def org_equipments(user: AbstractUser) -> QuerySet:
    """get all task associated to user's org"""
    # If the user is None, has no ID or is not active
    # return an empty queryset
    if not user or not user.id or not user.is_active:
        return Equipment.objects.none()

    # find only orgs that the user is associated to and that
    # are active
    orgs = [
        o.organization
        for o in OrganizationUser.objects.filter(user_id=user.id).select_related("organization")
        if o.organization.is_active
    ]
    equipments = Equipment.objects.filter(org__in=orgs)
    return equipments


def get_equipment_type(data):
    """get all unique equipment_type"""
    data = data.values_list("equipment_type", flat=True)
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
def equipments(request):
    "Equipments view"
    sort = request.GET.get("sort", "name")
    page = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 15)
    filter_by = request.GET.get("filter_by", None)
    param = request.GET.get("param", None)

    data = org_equipments(request.user)
    equipment_type = get_equipment_type(data)
    vendors = get_vendors(data)

    if param:
        if filter_by == "type":
            data = data.filter(equipment_type=param)
        elif filter_by == "vendor":
            if param == "None":
                data = data.filter(vendor__isnull=True)
            else:
                data = data.filter(vendor__contains=param)

    table = EquipmentTable(data=data, order_by=sort)
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
    table = EquipmentTable(data=data, order_by=sort, template_name="table/custome_table.html")
    table.paginate(page=page, per_page=page_size)

    context = {
        "segment": "equipments",
        "tabledata": table,
        "organization": get_user_org(request.user),
        "organization_pk": get_user_org(request.user).id if get_user_org(request.user) else "",
        "equipment_type": equipment_type,
        "vendors": vendors,
    }
    return HttpResponse(loader.get_template("equipments/index.html").render(context, request))


@login_required
def equipment(request, equipment_id=None):
    "Equipment create view" 

    section = "Equipment"

    model = get_object_or_404(org_equipments(request.user), pk=equipment_id) if equipment_id else Equipment(org=None)
    model.org = model.org if hasattr(model, "org") else get_user_org(request.user)


    if request.method == "POST":
        form = EquipmentForm(request.POST, model=model, instance=model)
        if form.is_valid():
            model = form.save(commit=False)
            model.save()
            return HttpResponseRedirect(reverse("equipments"))

    else:
        form = EquipmentForm(model=model, initial=model.__dict__)

    context = {
        "segment": "equipments",
        "model": model,
        "form": form,
        "organization": get_user_org(request.user),
        "section": section,
        "resource_option_vendor": get_resource_option_list_vendor(request.user),
        "resource_option_process": get_resource_option_list_vendor_process(request.user),
    }
    return render(request, "equipments/equipment_form.html", context)