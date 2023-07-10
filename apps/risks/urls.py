from django.urls import include, path

from apps.risks import views

urlpatterns = [
    path("risks/", views.risks, name="risks"),
    path("risks/",
        include([
            path("create/", views.risk_view, name="risk-create"),
            path("<int:risk_id>/", views.risk_view, name="risk-edit"),
        ]
    )
    )
]