from django.urls import path
from apps.djf_surveys.gracen_admin import views as admin_views


urlpatterns = [
    path("", admin_views.surveys, name="gracen_admin_survey"),
    path("import/questionnaire", admin_views.import_survey, name="gracen_admin_survey_import"),
    path("create/questionnaire/", admin_views.AdminCrateSurveyView.as_view(), name="gracen_admin_create_survey"),
    path("edit/questionnaire/<str:slug>/", admin_views.AdminEditSurveyView.as_view(), name="gracen_admin_edit_survey"),
    path(
        "delete/questionnaire/<str:slug>/",
        admin_views.AdminDeleteSurveyView.as_view(),
        name="gracen_admin_delete_survey",
    ),
    path("forms/<str:slug>/", admin_views.AdminSurveyFormView.as_view(), name="gracen_admin_forms_survey"),
    path("question/add/<int:pk>/", admin_views.AdminCreateQuestionView.as_view(), name="gracen_admin_create_question"),
    path("question/edit/<int:pk>/", admin_views.AdminUpdateQuestionView.as_view(), name="gracen_admin_edit_question"),
    path(
        "question/delete/<int:pk>/", admin_views.AdminDeleteQuestionView.as_view(), name="gracen_admin_delete_question"
    ),
    path(
        "question/ordering/",
        admin_views.AdminChangeOrderQuestionView.as_view(),
        name="gracen_admin_change_order_question",
    ),
    path("question/view/<int:pk>/", admin_views.AdminQuestionFormView.as_view(), name="gracen_admin_question_list"),
    path(
        "download/questionnaire/<str:slug>/",
        admin_views.DownloadResponseSurveyView.as_view(),
        name="gracen_admin_download_survey",
    ),
    path(
        "summary/questionnaire/<str:slug>/",
        admin_views.SummaryResponseSurveyView.as_view(),
        name="gracen_admin_summary_survey",
    ),
    path("edit/<int:pk>/", admin_views.EditSurveyQuestionFormView.as_view(), name="gracen_admin_edit"),
    path("create/<str:slug>/", admin_views.CreateSurveyQuestionFormView.as_view(), name="gracen_admin_create"),
    path("vendor/update/grc_version/<int:pk>", admin_views.update_gracen_version, name="update_grc_version"),
    path("detail/questionnaire/<int:pk>/", admin_views.survey_import_details, name="gracen_admin_survey_details"),
]
