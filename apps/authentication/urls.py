# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import include, path

from .views import (
    OrganizationUserEdit,
    OrganizationUserInvite,
    OrganizationUserListView,
    OrganizationUserRemind,
    OrganizationUserRemove,
    survey_login,
    survey_logout,
)

urlpatterns = [
    path(
        "organizations/<int:organization_pk>/",
        include(
            [
                path(
                    "users/",
                    include(
                        [
                            path("", OrganizationUserListView.as_view(), name="org_user_list"),
                            path("invite/", OrganizationUserInvite.as_view(), name="org_user_invite"),
                            path("<int:org_user_pk>/", OrganizationUserEdit.as_view(), name="org_user_edit"),
                            path(
                                "<int:org_user_pk>/remind/", OrganizationUserRemind.as_view(), name="org_user_remind"
                            ),
                            path(
                                "<int:org_user_pk>/remove/", OrganizationUserRemove.as_view(), name="org_user_remove"
                            ),
                        ]
                    ),
                ),
            ]
        ),
    ),
    path("questionnaire/<token>", survey_login, name="survey-login"),
    path("questionnaire/<token>/logout", survey_logout, name="survey-logout"),
]
