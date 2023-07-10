from django.urls import include, path

from apps.systems import views

urlpatterns = [
    path(
        "system/",
        include(
            [
                path("", views.systems, name="systems"),
                path("create", views.system, name="system-create"),
                path("edit/<int:system_id>", views.system, name="system-edit")
            ]
        )
    )
]