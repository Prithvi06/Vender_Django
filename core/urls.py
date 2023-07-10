# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.generic.base import TemplateView
from organizations.backends import invitation_backend

urlpatterns = [
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path("admin/", admin.site.urls),
    path("", include("apps.authentication.urls")),
    path("", include("apps.vendor.urls")),
    path("", include("apps.home.urls")),
    re_path(r"^invitations/", include(invitation_backend().get_urls())),
    path("", include("apps.administrator.urls")),
    path("", include("apps.incidents.urls")),
    path("", include("apps.tasks.urls")),
    path("", include("apps.risks.urls")),
    path("", include("apps.notes.urls")),
    # Survey urls
    path("questionnaire/", include("apps.djf_surveys.urls")),
    path("", include("apps.equipments.urls")),
    path("", include("apps.systems.urls")),
    # registering a redirect for signup before registering allauth.urls
    # prevents users from getting to the signup page.
    path("accounts/signup/", RedirectView.as_view(url="/accounts/login")),
    path("accounts/", include("allauth.urls")),
]
