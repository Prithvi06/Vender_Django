from django.urls import path
from apps.djf_surveys.admins import views as admin_views


urlpatterns = [
    path("", admin_views.org_surveys, name="admin_survey"),
    path("create/questionnaire/", admin_views.AdminCrateSurveyView.as_view(), name="admin_create_survey"),
    path("edit/questionnaire/<str:slug>/", admin_views.AdminEditSurveyView.as_view(), name="admin_edit_survey"),
    path("delete/questionnaire/<str:slug>/", admin_views.AdminDeleteSurveyView.as_view(), name="admin_delete_survey"),
    path("forms/<str:slug>/", admin_views.AdminSurveyFormView.as_view(), name="admin_forms_survey"),
    path("question/add/<int:pk>/", admin_views.AdminCreateQuestionView.as_view(), name="admin_create_question"),
    path("question/edit/<int:pk>/", admin_views.AdminUpdateQuestionView.as_view(), name="admin_edit_question"),
    path("question/delete/<int:pk>/", admin_views.AdminDeleteQuestionView.as_view(), name="admin_delete_question"),
    path("question/ordering/", admin_views.AdminChangeOrderQuestionView.as_view(), name="admin_change_order_question"),
    path("question/view/<int:pk>/", admin_views.AdminQuestionFormView.as_view(), name="admin_question_list"),
    path(
        "question/view/<int:pk>/document-view", admin_views.view_question_document, name="admin_question_document_view"
    ),
    path(
        "download/questionnaire/<str:slug>/",
        admin_views.DownloadResponseSurveyView.as_view(),
        name="admin_download_survey",
    ),
    path(
        "summary/questionnaire/<str:slug>/",
        admin_views.SummaryResponseSurveyView.as_view(),
        name="admin_summary_survey",
    ),
    path("edit/<int:pk>/", admin_views.EditSurveyQuestionFormView.as_view(), name="admin_edit"),
    path("create/<str:slug>/", admin_views.CreateSurveyQuestionFormView.as_view(), name="admin_create"),
    path("import-questionnaire/", admin_views.import_questionnaire, name="admin_import_questionnaire"),
    path("vendor/update/org_version/<int:pk>", admin_views.update_admin_org_version, name="update_org_version"),
    path("detail/questionnaire/<int:pk>/", admin_views.survey_import_details, name="admin_survey_details"),
]
