# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import include, path

from apps.incidents import views

urlpatterns = [
    path("incidents/", views.incidents, name="incidents"),
    path("incident/",
        include([
            path("create/", views.incident_view, name="incident-create"),
            path("<int:incident_id>/", views.incident_view, name="incident-edit"),
        ]
    )
    )
]
