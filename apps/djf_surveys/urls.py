from django.urls import path, include
from apps.djf_surveys import views
from apps.djf_surveys.app_settings import SURVEYS_ADMIN_BASE_PATH

app_name = "djf_surveys"
urlpatterns = [
    path("", views.SurveyListView.as_view(), name="index"),
    path("detail/<str:slug>/", views.DetailSurveyView.as_view(), name="detail"),
    path("edit/<int:pk>/", views.EditSurveyFormView.as_view(), name="edit"),
    path("detail/result/<int:pk>/", views.DetailResultSurveyView.as_view(), name="detail_result"),
    path("create/<str:slug>/", views.CreateSurveyFormView.as_view(), name="create"),
    path("delete/<int:pk>/", views.DeleteSurveyAnswerView.as_view(), name="delete"),
    path(SURVEYS_ADMIN_BASE_PATH, include("apps.djf_surveys.admins.urls")),
    path("administrator/", include("apps.djf_surveys.gracen_admin.urls")),
    path("question/add/<int:pk>/", views.VendorCreateQuestionView.as_view(), name="create_question"),
    path("question/edit/<int:pk>/", views.VendorUpdateQuestionView.as_view(), name="edit_question"),
    path("question/delete/<int:pk>/", views.VendorDeleteQuestionView.as_view(), name="delete_question"),
    path("question/ordering/", views.VendorChangeOrderQuestionView.as_view(), name="change_order_question"),
    path("question/view/<int:pk>/document-view", views.view_question_document, name="question_document_view"),
    path("vendor/edit/<int:pk>/", views.VendorEditSurveyFormView.as_view(), name="vendor_edit_survey"),
    path("vendor/create/<str:slug>/", views.VendorCreateSurveyFormView.as_view(), name="vendor_create_survey"),
    path("<token>/edit/<int:pk>/", views.InviteEditSurveyFormView.as_view(), name="invite-survey-edit"),
    path("<token>/create/<str:slug>/", views.InviteCreateSurveyFormView.as_view(), name="invite-survey-create"),
    path("<token>/status/", views.invite_questionnarie_redirect, name="invite_questionnarie_redirect"),
    path("question-header/<int:question_id>/", views.create_question_header, name="create_question_header"),
    path("question-header-remove/<int:question_id>/", views.remove_question_header, name="question_header_remove"),
    path("question-header-update/<int:question_id>/", views.update_question_header, name="question_header_update"),
]
