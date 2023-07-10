from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AbstractUser
from django.core.mail import EmailMessage
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import loader
from django.urls import reverse
from organizations.models import Organization, OrganizationUser

from apps.utility.EmailServices import email_service
from apps.vendor.models import Vendor
from core.settings.base import FROM_EMAIL

from .models import BusinessUnit, Department, OrganizationSetting, Process, Location, BusinessProcess
from .forms import LocationForm
from django.db.models import Q, QuerySet
from .tables import LocationTable
import math
from django.shortcuts import get_object_or_404, render
from apps.administrator.tasks import location_search, location_report
from apps.utility.VendorUtilities import org_vendors


class GracenConstraints:
    BUSINESS_PROCESS = ["UNIT", "DEPARTMENT", "PROCESS"]


def get_user_org(user: AbstractUser) -> Organization:
    """get first org user is associated to"""
    if not user or not user.id or not user.is_active:
        return None

    orguser = OrganizationUser.objects.select_related("organization").filter(user=user).first()
    return orguser.organization if orguser else None


def get_vendor_categories(user):
    """get all unique categories across all vendors"""
    data = (
        Vendor.objects.filter(org=get_user_org(user)).values_list("category", flat=True).filter(category__isnull=False)
    )
    unique = set(data)
    result = list(unique)
    result.sort()
    return result


@login_required
def admin_home(request, organization_pk):
    """admin view"""
    context = {
        "segment": ["administrator"],
        "organization": get_user_org(request.user),
        "organization_pk": get_user_org(request.user).id,
    }
    return HttpResponse(loader.get_template("administrator/index.html").render(context, request))


@login_required
def field_values(request, organization_pk):
    """fields value view"""
    category = get_vendor_categories(request.user)
    context = {
        "organization": get_user_org(request.user),
        "organization_pk": get_user_org(request.user).id,
        "category": category,
    }
    return HttpResponse(loader.get_template("administrator/field_values.html").render(context, request))


@login_required
def category(request, organization_pk, category_name):
    vendor_obj = Vendor.objects.filter(org_id=organization_pk, category=category_name)
    if request.method == "POST":
        vendor_obj.update(category=request.POST["name"])
        return HttpResponseRedirect(reverse("field-values", args=[organization_pk]))
    elif request.path.endswith("delete"):
        vendor_obj.update(category=None)
        return HttpResponseRedirect(reverse("field-values", args=[organization_pk]))
    else:
        data = {"count": vendor_obj.count()}
        return JsonResponse(data)


@login_required
def create_business_units(request, organization_pk):
    if request.method == "POST":
        org_obj = Organization.objects.filter(id=organization_pk).first()
        unit_obj = BusinessUnit.objects.create(organization=org_obj, name=request.POST["name"])
        unit_id = unit_obj.id
        BusinessProcess.objects.create(organization=org_obj, unit=unit_obj)
    return HttpResponseRedirect(reverse("unit_organization_setup", args=[organization_pk, unit_id]))


@login_required
def business_units(request, organization_pk, unit_id):
    business_object = BusinessUnit.objects.filter(organization_id=organization_pk, id=unit_id)
    if request.method == "POST":
        business_object.update(name=request.POST["name"])
        return HttpResponseRedirect(reverse("unit_organization_setup", args=[organization_pk, unit_id]))
    elif request.path.endswith("delete"):
        business_object.update(is_deleted=True)
        org_obj = Organization.objects.filter(id=organization_pk).first()
        business_obj = BusinessProcess.objects.filter(organization=org_obj, unit=business_object.first())
        business_obj.delete()
        return HttpResponseRedirect(reverse("organization_setup", args=[organization_pk]))


@login_required
def create_departments(request, organization_pk):
    unit_id = request.GET.get("unit_id")
    if request.method == "POST":
        org_obj = Organization.objects.filter(id=organization_pk).first()
        if unit_id != "None":
            unit_object = BusinessUnit.objects.filter(organization_id=organization_pk, id=unit_id).first()
            department_obj = Department.objects.create(
                organization=org_obj, unit=unit_object, name=request.POST["name"]
            )
            department_id = department_obj.id
            if department_obj.unit:
                business_obj = BusinessProcess.objects.filter(organization=org_obj, unit=department_obj.unit)
                if business_obj.first() and not business_obj.first().department:
                    business_obj.update(department=department_obj)
                else:
                    BusinessProcess.objects.create(organization=org_obj, unit=unit_object, department=department_obj)
                unit_id = department_obj.unit.id
                return HttpResponseRedirect(
                    reverse("unit_departartment_organization_setup", args=[organization_pk, unit_id, department_id])
                )
            else:
                return HttpResponseRedirect(
                    reverse("departartment_organization_setup", args=[organization_pk, department_id])
                )
        else:
            return HttpResponseRedirect(reverse("organization_setup", args=[organization_pk]))
    return HttpResponseRedirect(reverse("organization_setup", args=[organization_pk]))


@login_required
def departments(request, organization_pk, department_id):
    department_object = Department.objects.filter(organization_id=organization_pk, id=department_id)
    if request.method == "POST":
        department_object.update(name=request.POST["name"])
        if department_object.first().unit:
            unit_id = department_object.first().unit.id
            return HttpResponseRedirect(
                reverse("unit_departartment_organization_setup", args=[organization_pk, unit_id, department_id])
            )
        else:
            return HttpResponseRedirect(
                reverse("departartment_organization_setup", args=[organization_pk, department_id])
            )
    elif request.path.endswith("delete"):
        department_object.update(is_deleted=True)
        if department_object.first().unit:
            business_obj = BusinessProcess.objects.filter(organization=department_object.first().organization,
                                                          unit=department_object.first().unit,
                                                          department=department_object.first())
            business_obj.delete()
            unit_id = department_object.first().unit.id
            return HttpResponseRedirect(reverse("unit_organization_setup", args=[organization_pk, unit_id]))
        else:
            return HttpResponseRedirect(reverse("organization_setup", args=[organization_pk]))


@login_required
def create_processes(request, organization_pk):
    department_id = request.GET.get("department_id")
    if request.method == "POST":
        org_obj = Organization.objects.filter(id=organization_pk).first()
        if department_id != "None":
            department_object = Department.objects.filter(organization_id=organization_pk, id=department_id).first()
            process_object = Process.objects.create(
                organization=org_obj, department=department_object, name=request.POST["name"]
            )
            if process_object.department:
                department_id = process_object.department.id
                if process_object.department.unit:
                    business_obj = BusinessProcess.objects.filter(organization=org_obj,
                                                                  unit=process_object.department.unit,
                                                                  department=process_object.department)
                    if business_obj.first() and not business_obj.first().process:
                        business_obj.update(process=process_object)
                    else:
                        BusinessProcess.objects.create(organization=org_obj, unit=process_object.department.unit,
                                                       department=process_object.department, process=process_object)
                    
                    unit_id = process_object.department.unit.id
                    return HttpResponseRedirect(
                        reverse(
                            "unit_departartment_organization_setup", args=[organization_pk, unit_id, department_id]
                        )
                    )
                else:
                    return HttpResponseRedirect(
                        reverse("departartment_organization_setup", args=[organization_pk, department_id])
                    )
            else:
                return HttpResponseRedirect(reverse("organization_setup", args=[organization_pk]))
        return HttpResponseRedirect(reverse("organization_setup", args=[organization_pk]))
    return HttpResponseRedirect(reverse("organization_setup", args=[organization_pk]))


@login_required
def processes(request, organization_pk, process_id):
    process_object = Process.objects.filter(organization_id=organization_pk, id=process_id)
    if request.method == "POST":
        process_object.update(name=request.POST["name"])
        if process_object.first().department:
            department_id = process_object.first().department.id
            if process_object.first().department.unit:
                unit_id = process_object.first().department.unit.id
                return HttpResponseRedirect(
                    reverse("unit_departartment_organization_setup", args=[organization_pk, unit_id, department_id])
                )
            else:
                return HttpResponseRedirect(
                    reverse("departartment_organization_setup", args=[organization_pk, department_id])
                )
        else:
            return HttpResponseRedirect(reverse("organization_setup", args=[organization_pk]))
    elif request.path.endswith("delete"):
        process_object.update(is_deleted=True)
        if process_object.first().department:
            department_id = process_object.first().department.id
            if process_object.first().department.unit:
                business_obj = BusinessProcess.objects.filter(organization=process_object.first().organization,
                                                              unit=process_object.first().department.unit,
                                                              department=process_object.first().department,
                                                              process=process_object.first())
                business_obj.delete()
                unit_id = process_object.first().department.unit.id
                return HttpResponseRedirect(
                    reverse("unit_departartment_organization_setup", args=[organization_pk, unit_id, department_id])
                )
            else:
                return HttpResponseRedirect(
                    reverse("departartment_organization_setup", args=[organization_pk, department_id])
                )
        else:
            return HttpResponseRedirect(reverse("organization_setup", args=[organization_pk]))


@login_required
def organization_setup(request, organization_pk, unit_id=None, department_id=None):
    """fields value view"""
    category = get_vendor_categories(request.user)
    organization_object = OrganizationSetting.objects.filter(organization_id=organization_pk)
    unit_object = None
    department_obj = None
    process_object = None
    sel_unit = unit_id
    sel_dep = department_id
    unit_name = None
    department_name = None
    unit_object = (
        BusinessUnit.objects.filter(organization_id=organization_pk, is_deleted=False).order_by("name").distinct()
    )
    department_obj = Department.objects.filter(organization_id=organization_pk, is_deleted=False).distinct()
    process_object = Process.objects.filter(organization_id=organization_pk, is_deleted=False).distinct()

    if organization_object:
        if unit_id and unit_id != "UNIT":
            department_obj = department_obj.filter(unit_id=unit_id).distinct()
        elif not unit_id and unit_object:
            sel_unit = unit_object.first().id
            department_obj = department_obj.filter(unit=unit_object.first()).distinct()
            unit_name = unit_object.first().name
        if department_id:
            process_object = process_object.filter(department_id=department_id).distinct()
        elif department_id == None and department_obj.exists():
            sel_dep = department_obj.first().id
            process_object = process_object.filter(department=department_obj.first()).distinct()
            department_name = department_obj.first().name
        if not department_obj:
            process_object = None

    if unit_id:
        unit_obj = BusinessUnit.objects.filter(id=unit_id, organization_id=organization_pk, is_deleted=False).first()
        unit_name = unit_obj.name if unit_obj else None
    if department_id:
        department_object = Department.objects.filter(
            id=department_id, organization_id=organization_pk, is_deleted=False
        ).first()
        department_name = department_object.name if department_object else None

    context = {
        "segment": ["administrator", "field values"],
        "organization": get_user_org(request.user),
        "organization_pk": get_user_org(request.user).id,
        "category": category,
        "business_units": unit_object,
        "departments": department_obj,
        "processes": process_object,
        "sel_unit": int(sel_unit) if sel_unit and sel_unit != GracenConstraints.BUSINESS_PROCESS[0] else sel_unit,
        "sel_dep": int(sel_dep) if sel_dep else sel_dep,
        "unit_name": unit_name,
        "department_name": department_name,
    }
    return HttpResponse(loader.get_template("administrator/organization_setup.html").render(context, request))


# Gracen admin


@login_required(login_url="/login/")
def gracen_admin_home(request):
    context = {"segment": "dashboard"}
    return HttpResponse(loader.get_template("administrator/gracen/index.html").render(context, request))


def get_address_line1(data):
    """get all unique vendor residual risk"""
    data = data.values_list("line_1", flat=True)
    unique = set(data)
    result = list(unique)
    # result.sort()
    return result


def get_city(data):
    """get all unique vendor residual risk"""
    data = data.values_list("city", flat=True)
    unique = set(data)
    result = list(unique)
    # result.sort()
    return result


def get_location_type(data):
    """get all unique vendor residual risk"""
    data = data.values_list("location_type", flat=True)
    unique = set(data)
    result = list(unique)
    # result.sort()
    return result


def org_locations(user: AbstractUser) -> QuerySet:
    """get all locations associated to user's org"""
    # If the user is None, has no ID or is not active
    # return an empty queryset
    if not user or not user.id or not user.is_active:
        return Location.objects.none()

    # find only orgs that the user is associated to and that
    # are active
    orgs = [
        o.organization
        for o in OrganizationUser.objects.filter(user_id=user.id).select_related("organization")
        if o.organization.is_active
    ]
    locations = Location.objects.filter(org__in=orgs)
    return locations


@login_required
def locations(request, organization_pk):
    """locations view"""
    organization_object = OrganizationSetting.objects.filter(organization_id=organization_pk)
    sort = request.GET.get("sort", "title")
    page = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 15)
    search = request.GET.get("search", "")
    param = request.GET.get("param", None)
    filter_by = request.GET.get("filter_by", None)

    user = request.user
    data = org_locations(user)
    address_line1 = get_address_line1(data)
    city = get_city(data)
    location_type = get_location_type(data)

    if search:
        data_by_name = data.filter(name__icontains=search)
        data_by_location_type = data.filter(location_type__icontains=search)
        data_by_city = data.filter(city__icontains=search)
        data_by_address = data.filter(line_1__icontains=search)
        data = (data_by_name | data_by_location_type | data_by_city | data_by_address).distinct()

    if param:
        if filter_by == "type":
            if param == "None":
                data = data.filter(location_type__isnull=True)
            else:
                data = data.filter(location_type=param)
        elif filter_by == "city":
            if param == "None":
                data = data.filter(city__isnull=True)
            else:
                data = data.filter(city=param)

    table = LocationTable(data=data, order_by=sort)
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
    table = LocationTable(data=data, order_by=sort, template_name="table/custome_table.html")
    table.paginate(page=page, per_page=page_size)
    context = {
        "segment": ["administrator", "locations"],
        "tabledata": table,
        "organization": get_user_org(request.user),
        "organization_pk": get_user_org(request.user).id if get_user_org(request.user) else "",
        "city": city,
        "location_type": location_type,
    }
    return HttpResponse(loader.get_template("administrator/location.html").render(context, request))


def get_user_org(user: AbstractUser) -> Organization:
    """get first org user is associated to"""
    if not user or not user.id or not user.is_active:
        return None

    orguser = OrganizationUser.objects.select_related("organization").filter(user=user).first()
    return orguser.organization if orguser else None


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
def location_create(request, organization_pk, location_id=None):
    "location create view"

    section = "Location"
    ofac_results = None

    model = get_object_or_404(org_locations(request.user), pk=location_id) if location_id else Location(org=None)
    model.org = model.org if hasattr(model, "org") else get_user_org(request.user)

    if request.method == "POST":
        form = LocationForm(request.POST, model=model, instance=model)
        if form.is_valid():
            model = form.save(commit=False)
            model.save()
            ofac_results = location_search(model)
            if ofac_results:
                context = {
                    "segment": ["administrator", "locations"],
                    "model": model,
                    "form": form,
                    "organization": get_user_org(request.user),
                    "section": section,
                    "ofac_results": ofac_results,
                }
                return render(request, "administrator/location_form.html", context)
    else:
        form = LocationForm(model=model, initial=model.__dict__)

    context = {
        "segment": ["administrator", "locations"],
        "model": model,
        "form": form,
        "organization": get_user_org(request.user),
        "section": section,
        "ofac_results": ofac_results,
        "resource_option_vendor": get_resource_option_list_vendor(request.user),
        "resource_option_process": get_resource_option_list_vendor_process(request.user),
    }
    return render(request, "administrator/location_form.html", context)


@login_required(login_url="/login/")
def ignore_ofac_result(request, organization_pk, location_id: int):

    if location_id:
        location = Location.objects.filter(pk=location_id)
        location.update(ignore_sdn=True)
        section = "TASK"
        section_data = request.GET.get("section", "")
        if section_data:
            section = section_data
        return HttpResponseRedirect(
            reverse("location-edit", args=[organization_pk, location_id]) + "?section=" + section
        )


@login_required(login_url="/login/")
def create_ofac_result_task(request, organization_pk, location_id: int):

    if location_id:
        location_report(location_id)
        section = "TASK"
        section_data = request.GET.get("section", "")
        if section_data:
            section = section_data
        return HttpResponseRedirect(
            reverse("location-edit", args=[organization_pk, location_id]) + "?section=" + section
        )
