# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import include, path

from apps.tasks import views

urlpatterns = [
    path("tasks/", views.tasks, name="tasks"),
    path(
        "task/",
        include(
            [
                path("create", views.task_view, name="task-create"),
                path("risk/<risk_id>/create", views.task_view, name="risk-task-create"),
                path("incident/<incident_id>/create", views.task_view, name="incident-task-create"),
                path("child-task/<parent_task_id>/create", views.task_view, name="child-task-create"),
                path("<int:task_id>", views.task_view, name="task-edit"),
                path("<int:task_id>/risk/<risk_id>", views.task_view, name="risk-task-edit"),
                path("<int:task_id>/incident/<incident_id>", views.task_view, name="incident-task-edit"),
                path("vendor/<vendor_id>/create", views.task_view, name="vendor-task-create"),
                path("<int:task_id>/vendor/<vendor_id>", views.task_view, name="vendor-task-edit"),
                path("<int:task_id>/child-task/<parent_task_id>", views.task_view, name="child-task-edit"),
                path("<int:task_id>/delete", views.task_view, name="task-delete"),
                path("<int:task_id>/risk/<risk_id>/delete", views.task_view, name="risk-task-delete"),
                path("<int:task_id>/incident/<incident_id>/delete", views.task_view, name="incident-task-delete"),
                path("<int:task_id>/vendor/<vendor_id>/delete", views.task_view, name="vendor-task-delete"),
                path("<int:task_id>/child-task/<parent_task_id>/delete", views.task_view, name="child-task-delete"),
            ]
        ),
    ),
]
