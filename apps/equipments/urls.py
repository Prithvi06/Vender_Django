from django.urls import include, path

from apps.equipments import views

urlpatterns = [
    path(
        "equipment/",
        include(
            [
                path("", views.equipments, name="equipments"),
                path("create", views.equipment, name="equipment-create"),
                path("edit/<int:equipment_id>", views.equipment, name="equipment-edit")
            ]
        )
    )
]