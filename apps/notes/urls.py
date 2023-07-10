from django.urls import path, include
from . import views

urlpatterns = [
    path(
        "notetest/",
        include(
            [
                path("create/<int:task_id>", views.log_comments, name="create-task-notes"),
                path("edit/<int:id>/task/<int:task_id>", views.log_comments, name="edit-task-notes"),
                path("create/contact/<int:contact_id>", views.log_comments, name="create-contact-notes"),
                path("edit/<int:id>/contact/<int:contact_id>", views.log_comments, name="edit-contact-notes"),
                path("create/incident/<int:incident_id>", views.log_comments, name="create-incident-notes"),
                path("edit/<int:id>/incident/<int:incident_id>", views.log_comments, name="edit-incident-notes"),
                path("create/risk/<int:risk_id>", views.log_comments, name="create-risk-notes"),
                path("edit/<int:id>/risk/<int:risk_id>", views.log_comments, name="edit-risk-notes"),
                path("create/survey/<int:survey_id>", views.log_comments, name="create-survey-notes"),
                path("edit/<int:id>/survey/<int:survey_id>", views.log_comments, name="edit-survey-notes"),
            ]
        ),
    )
]
