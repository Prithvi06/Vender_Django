# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import include, path

from apps.vendor import views

urlpatterns = [
    path(
        "dashboard/",
        include(
            [
                path("", views.dashboard, name="dashboard"),
                path(
                    "reports/",
                    include(
                        [
                            path("", views.reports, name="reports"),
                            path("critical-third-parties", views.reports, name="critical-third-parties"),
                            path("third-party-directory", views.reports, name="third-party-directory"),
                            path("task-reports", views.reports, name="task-reports"),
                            path("incidents-reports", views.reports, name="incidents-reports"),
                            path("expiring-contracts-reports", views.reports, name="expiring-contracts-reports"),
                            path("risk-reports", views.reports, name="risk-reports"),
                            path("renew-contracts-reports", views.reports, name="renew-contracts-reports"),
                        ]
                    ),
                ),
            ]
        ),
    ),
    path(
        "vendors/",
        include(
            [
                path("", views.vendors, name="vendors"),
                path("create/", views.vendor, name="vendor-create"),
                path("<int:vendor_id>/", views.vendor, name="vendor-edit"),
                path("<int:vendor_id>/contacts/create/", views.contact, name="contact-create"),
                path("<int:vendor_id>/contacts/<int:contact_id>/", views.contact, name="contact-edit"),
                path("<int:vendor_id>/contacts/<int:contact_id>/delete", views.contact, name="contact-delete"),
                path("<int:vendor_id>/contacts/<int:contact_id>/phones/create/", views.phone, name="phone-create"),
                path(
                    "<int:vendor_id>/contacts/<int:contact_id>/phones/<int:phone_id>/", views.phone, name="phone-edit"
                ),
                path(
                    "<int:vendor_id>/contacts/<int:contact_id>/phones/<int:phone_id>/delete",
                    views.phone,
                    name="phone-delete",
                ),
                path("<int:vendor_id>/contracts/create/", views.contract, name="contract-create"),
                path("<int:vendor_id>/contracts/create/<popup>", views.contract, name="pop-contract-create"),
                path("<int:vendor_id>/contracts/<int:contract_id>/", views.contract, name="contract-edit"),
                path("<int:vendor_id>/contracts/<int:contract_id>/delete", views.contract, name="contract-delete"),
                path(
                    "<int:vendor_id>/contracts/<int:contract_id>/links/",
                    views.contract_links,
                    name="contract-links",
                ),
                path(
                    "<int:vendor_id>/contracts/<int:contract_id>/links/<int:child_contract_id>/<str:relation_type>",
                    views.contract_links,
                    name="contract-links",
                ),
                path(
                    "<int:vendor_id>/contracts/<int:contract_id>/documents/create/",
                    views.document,
                    name="document-create",
                ),
                path(
                    "<int:vendor_id>/contracts/<int:contract_id>/documents/<int:document_id>/",
                    views.document,
                    name="document-edit",
                ),
                path(
                    "<int:vendor_id>/contracts/<int:contract_id>/documents/<int:document_id>/view",
                    views.document,
                    name="document-view",
                ),
                path(
                    "<int:vendor_id>/contracts/<int:contract_id>/document/<int:document_id>/delete",
                    views.document,
                    name="document-delete",
                ),
                path(
                    "<int:vendor_id>/additional-details",
                    views.addition_details,
                    name="additional-details",
                ),
                path(
                    "<int:vendor_id>/documents/create/",
                    views.documents,
                    name="documents-create",
                ),
                path(
                    "<int:vendor_id>/documents/<int:document_id>/",
                    views.documents,
                    name="documents-edit",
                ),
                path(
                    "<int:vendor_id>/documents/<int:document_id>/view",
                    views.documents,
                    name="documents-view",
                ),
                path(
                    "<int:vendor_id>/documents/<int:document_id>/delete",
                    views.documents,
                    name="documents-delete",
                ),
                path(
                    "<int:vendor_id>/ofac-tasks-ignore",
                    views.ignore_ofac_result,
                    name="ignore-ofac-result",
                ),
                path(
                    "<int:vendor_id>/ofac-tasks-create",
                    views.create_ofac_result_task,
                    name="create-ofac-result-task",
                ),
                path(
                    "<int:vendor_id>/contacts/<int:contact_id>/ofac-tasks-ignore",
                    views.ignore_ofac_result,
                    name="ignore-ofac-result",
                ),
                path(
                    "<int:vendor_id>/contacts/<int:contact_id>/ofac-tasks-create",
                    views.create_ofac_result_task,
                    name="create-ofac-result-task",
                ),
                path("<int:vendor_id>/import-questionnaire", views.import_questionnaire, name="import-questionnaire"),
                path("send-questionnaire/<int:survey_id>", views.send_to_vendor, name="send-questionnaire"),
                path("<int:vendor_id>/questionnaire", views.vendor_surveys, name="vendor_surveys"),
                path(
                    "<int:vendor_id>/documents/create/<str:popup>",
                    views.documents,
                    name="documents-popup-create",
                ),
                path("contract/<int:vendor_id>/", views.get_vendor_contract, name="vendor-contract"),
                path(
                    "<int:vendor_id>/questionnaire/<int:survey_id>",
                    views.send_survey_to_vendor,
                    name="vendor-survey-link",
                ),
            ]
        ),
    ),
    path("contracts/", include([path("", views.contract_index, name="contract_index")])),
]
