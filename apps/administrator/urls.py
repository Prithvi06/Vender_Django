# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import include, path

from .views import (
    admin_home,
    gracen_admin_home,
    field_values,
    category,
    business_units,
    processes,
    departments,
    organization_setup,
    create_business_units,
    create_departments,
    create_processes,
    locations,
    location_create,
    ignore_ofac_result,
    create_ofac_result_task,
)

urlpatterns = [
    path(
        "organizations/<int:organization_pk>/",
        include(
            [
                path("", admin_home, name="administrator"),
                path("fields", field_values, name="field-values"),
                path("category/<str:category_name>", category, name="field-category"),
                path("category/<str:category_name>/delete", category, name="field-category-delete"),
                path("business-unit/<str:unit_id>", business_units, name="business-unit"),
                path("create-business-unit", create_business_units, name="create-business-unit"),
                path("business-unit/<str:unit_id>/delete", business_units, name="business-unit-delete"),
                path("business-process/<int:process_id>", processes, name="business-process"),
                path("create-business-process", create_processes, name="create-business-process"),
                path("business-process/<int:process_id>/delete", processes, name="business-process-delete"),
                path("business-department/<int:department_id>", departments, name="business-department"),
                path("create-business-department", create_departments, name="create-business-department"),
                path("business-department/<int:department_id>/delete", departments, name="business-department-delete"),
                path("setup", organization_setup, name="organization_setup"),
                path("setup-unit/<int:unit_id>", organization_setup, name="unit_organization_setup"),
                path(
                    "setup-department/<int:department_id>", organization_setup, name="departartment_organization_setup"
                ),
                path(
                    "setup/<int:unit_id>/<int:department_id>",
                    organization_setup,
                    name="unit_departartment_organization_setup",
                ),
                path("locations", locations, name="locations"),
                path("location/create", location_create, name="location-create"),
                path("location/<int:location_id>/", location_create, name="location-edit"),
                path(
                    "location/<int:location_id>/ofac-tasks-ignore",
                    ignore_ofac_result,
                    name="ignore-ofac-location-result",
                ),
                path(
                    "location/<int:location_id>/ofac-tasks-create",
                    create_ofac_result_task,
                    name="create-ofac-result-location-task",
                ),
            ]
        ),
    ),
    path("home", gracen_admin_home, name="gracen_admin_home"),
]
