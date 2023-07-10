import csv
import mimetypes
from io import StringIO
import math
from django.utils.text import capfirst
from django.utils.translation import gettext, gettext_lazy as _
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormMixin
from django.utils.decorators import method_decorator
from django.core.files.storage import default_storage

# from django.contrib.admin.views.decorators import is_admin_or_org_admin
from django.urls import reverse, reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.contrib import messages

from apps.djf_surveys.app_settings import SURVEYS_ADMIN_BASE_PATH
from apps.djf_surveys.models import (
    Survey,
    Question,
    UserAnswer,
    OrgAnswer,
    OrgQuestion,
    OrgSurvey,
    OrgUserAnswer,
    QuestionHeader,
    SurveyStatus,
)
from apps.djf_surveys.mixin import ContextTitleMixin
from apps.djf_surveys.views import OrgSurveyListView
from apps.djf_surveys.forms import (
    BaseSurveyForm,
    OrgAdminCreateSurveyForm,
    OrgAdminEditSurveyForm,
)
from apps.djf_surveys.summary import SummaryResponse
from apps.vendor.views import get_user_org
from django.shortcuts import render
from .decorators import is_admin_or_org_admin
from apps.utility.VendorUtilities import (
    org_vendors,
)
from django.db.models import Max
from .tables import SurveyTable


@method_decorator(is_admin_or_org_admin, name="dispatch")
class AdminCrateSurveyView(ContextTitleMixin, CreateView):
    model = OrgSurvey
    template_name = "djf_surveys/admin/survey_form.html"
    fields = [
        "name",
        "description",
        "active",
    ]
    title_page = _("Add New Survey")

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            survey = form.save()
            survey.org_id = get_user_org(self.request.user).pk
            survey.org_version = 1.00
            survey.status = SurveyStatus.NOT_SENT
            survey.save()
            self.success_url = reverse("djf_surveys:admin_edit_survey", args=[survey.slug])
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, *args, **kwargs):
        context = super(AdminCrateSurveyView, self).get_context_data(*args, **kwargs)
        context["segment"] = "administrator"
        context["organization"] = get_user_org(self.request.user)
        context["organization_pk"] = get_user_org(self.request.user).pk
        return context


@method_decorator(is_admin_or_org_admin, name="dispatch")
class AdminEditSurveyView(ContextTitleMixin, UpdateView):
    model = OrgSurvey
    template_name = "djf_surveys/admin/survey_form.html"
    fields = [
        "name",
        "description",
        "active",
    ]
    title_page = _("Edit Survey")

    def get_success_url(self):
        return reverse("djf_surveys:admin_survey")

    def get_context_data(self, *args, **kwargs):
        answer = OrgUserAnswer.objects.filter(user=self.request.user, survey=self.object)
        if answer.exists():
            self.object.answer = answer.first()
        else:
            self.object.answer = None
        context = super(AdminEditSurveyView, self).get_context_data(*args, **kwargs)
        context["segment"] = "administrator"
        context["question"] = OrgQuestion.objects.filter(survey=self.object)
        context["organization"] = get_user_org(self.request.user)
        context["organization_pk"] = get_user_org(self.request.user).pk
        return context


@is_admin_or_org_admin
def org_surveys(request):
    sort = request.GET.get("sort", "name")
    page = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 15)
    search = request.GET.get("search", "")
    org_question = Survey.objects.filter(active=True).order_by("name")
    org_surveys = OrgSurvey.objects.filter(org=get_user_org(request.user))
    if search:
        org_surveys = org_surveys.filter(name__icontains=search)
    table = SurveyTable(data=org_surveys, order_by=sort)
    total_data = org_surveys.count()
    if page_size == "All":
        page = 1
        page_size = total_data
    elif total_data < int(page_size) * int(page) and total_data != 0:
        if total_data > (int(page_size) * (int(page) - 1)):
            pass
        else:
            page_size = total_data
            page = int(math.ceil(int(page_size) * int(page) % total_data))
            if page <= 0:
                page = 1
    table.paginate(page=page, per_page=page_size)
    context = {
        "segment": "administrator",
        "organization": get_user_org(request.user),
        "organization_pk": get_user_org(request.user).pk,
        "org_question": org_question,
        "tabledata": table,
    }
    return render(request, "djf_surveys/admin/index.html", context)


@method_decorator(is_admin_or_org_admin, name="dispatch")
class AdminSurveyFormView(ContextTitleMixin, FormMixin, DetailView):
    model = OrgSurvey
    template_name = "djf_surveys/admin/survey_form.html"
    form_class = BaseSurveyForm

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(survey=self.object, user=self.request.user, **self.get_form_kwargs())

    def get_title_page(self):
        return self.object.name

    def get_sub_title_page(self):
        return self.object.description

    def get_context_data(self, *args, **kwargs):
        context = super(AdminSurveyFormView, self).get_context_data(*args, **kwargs)
        context["questions"] = OrgQuestion.objects.filter(survey=self.object)
        context["segment"] = "administrator"
        context["organization"] = get_user_org(self.request.user)
        context["organization_pk"] = get_user_org(self.request.user).pk
        return context


@method_decorator(is_admin_or_org_admin, name="dispatch")
class AdminDeleteSurveyView(DetailView):
    model = OrgSurvey

    def get(self, request, *args, **kwargs):
        survey = self.get_object()
        survey.delete()
        return redirect("djf_surveys:admin_survey")


@method_decorator(is_admin_or_org_admin, name="dispatch")
class AdminQuestionFormView(ContextTitleMixin, FormMixin, DetailView):
    model = OrgSurvey
    template_name = "djf_surveys/admin/question_preview.html"
    form_class = BaseSurveyForm
    survey = None

    def dispatch(self, request, *args, **kwargs):
        self.survey = get_object_or_404(OrgSurvey, id=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(survey=self.object, user=self.request.user, **self.get_form_kwargs())

    def get_title_page(self):
        return self.object.name

    def get_sub_title_page(self):
        return self.object.description

    def get_context_data(self, *args, **kwargs):
        context = super(AdminQuestionFormView, self).get_context_data(*args, **kwargs)
        context["question"] = OrgQuestion.objects.filter(survey=self.object)
        context["survey"] = self.survey
        context["segment"] = "administrator"
        context["organization"] = get_user_org(self.request.user)
        context["organization_pk"] = get_user_org(self.request.user).pk
        return context


@method_decorator(is_admin_or_org_admin, name="dispatch")
class AdminCreateQuestionView(ContextTitleMixin, CreateView):
    model = OrgQuestion
    template_name = "djf_surveys/admin/questions_form.html"
    success_url = reverse_lazy("djf_surveys:")
    fields = ["label", "type_field", "choices", "help_text", "required"]
    title_page = _("Add Question")
    survey = None

    def dispatch(self, request, *args, **kwargs):
        self.survey = get_object_or_404(OrgSurvey, id=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            total_question = OrgQuestion.objects.filter(survey=self.survey).aggregate(Max("ordering"))["ordering__max"]
            question = form.save(commit=False)
            question.survey = self.survey
            question.org_id = self.survey.org.id
            question.ordering = total_question + 1 if total_question else 1
            question.save()
            prev_question = OrgQuestion.objects.filter(ordering=question.ordering-1,
                                                       survey=self.survey)
            if prev_question:
                question.header = prev_question.first().header
            question.key = f"{str(get_user_org(self.request.user).pk)}-{self.survey.id}-{question.id}"
            question.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse("djf_surveys:admin_question_list", args=[self.survey.pk]) + "?Redirect=true"

    def get_context_data(self, *args, **kwargs):
        context = super(AdminCreateQuestionView, self).get_context_data(*args, **kwargs)
        context["segment"] = "administrator"
        context["survey"] = self.survey
        context["organization"] = get_user_org(self.request.user)
        context["organization_pk"] = get_user_org(self.request.user).pk
        return context


@method_decorator(is_admin_or_org_admin, name="dispatch")
class AdminUpdateQuestionView(ContextTitleMixin, UpdateView):
    model = OrgQuestion
    template_name = "djf_surveys/admin/questions_form.html"
    success_url = SURVEYS_ADMIN_BASE_PATH
    fields = ["label", "key", "type_field", "choices", "help_text", "required"]
    title_page = _("Add Question")
    survey = None

    def dispatch(self, request, *args, **kwargs):
        question = self.get_object()
        self.survey = question.survey
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        if self.model.id:
            return reverse("djf_surveys:admin_question_list", args=[self.survey.id])
        else:
            return reverse("djf_surveys:admin_edit_survey", args=[self.survey.slug])

    def get_context_data(self, *args, **kwargs):
        context = super(AdminUpdateQuestionView, self).get_context_data(*args, **kwargs)
        context["segment"] = "administrator"
        context["survey"] = self.survey
        context["organization"] = get_user_org(self.request.user)
        context["organization_pk"] = get_user_org(self.request.user).pk
        return context


@method_decorator(is_admin_or_org_admin, name="dispatch")
class AdminDeleteQuestionView(DetailView):
    model = OrgQuestion
    survey = None

    def dispatch(self, request, *args, **kwargs):
        question = self.get_object()
        self.survey = question.survey
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        question = self.get_object()
        question.delete()
        return redirect("djf_surveys:admin_question_list", pk=self.survey.id)


@method_decorator(is_admin_or_org_admin, name="dispatch")
class AdminChangeOrderQuestionView(View):
    def post(self, request, *args, **kwargs):
        ordering = request.POST["order_question"].split(",")
        ordering = [i for i in ordering if i != ""]
        order_question_id = request.POST["order_question_id"]
        on_header = request.POST["on_header"]
        question_object = OrgQuestion.objects.filter(pk=order_question_id)
        header_object = question_object.first().header
        survey_questions = OrgQuestion.objects.filter(survey=question_object.first().survey).order_by("ordering")

        for index, question_id in enumerate(ordering):
            if question_id:
                question = OrgQuestion.objects.get(id=question_id)
                if int(order_question_id) == int(question_id):
                    if header_object:
                        header_object = QuestionHeader.objects.filter(pk=header_object.pk)
                        if header_object:
                            header_question = survey_questions.filter(header=header_object.first())
                            if header_question.count() < 1:
                                header_object.delete()
                            else:
                                question.header = None
                    if (index - 1) >= 0:
                        prev_question = survey_questions.filter(pk=ordering[index - 1]).first()
                        question.header = prev_question.header
                    if on_header == "true" or on_header == True:
                        try:
                            next_question = survey_questions.filter(pk=ordering[index + 1]).first()
                            question.header = next_question.header
                        except Exception as e:
                            pass
                question.ordering = index
                question.save()

        data = {"message": gettext("Update ordering of questions succeeded.")}
        return JsonResponse(data, status=200)


@method_decorator(is_admin_or_org_admin, name="dispatch")
class DownloadResponseSurveyView(DetailView):
    model = Survey

    def get(self, request, *args, **kwargs):
        survey = self.get_object()
        user_answers = UserAnswer.objects.filter(survey=survey)
        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)

        rows = []
        header = []
        for index, user_answer in enumerate(user_answers):
            if index == 0:
                header.append("user")
                header.append("update_at")

            rows.append(user_answer.user.username if user_answer.user else "no auth")
            rows.append(user_answer.updated_at.strftime("%Y-%m-%d %H:%M:%S"))
            for answer in user_answer.answer_set.all():
                if index == 0:
                    header.append(answer.question.label)
                rows.append(answer.get_value_for_csv)

            if index == 0:
                writer.writerow(header)
            writer.writerow(rows)
            rows = []

        response = HttpResponse(csv_buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={survey.slug}.csv"
        return response


class SurveyFormView(FormMixin, DetailView):
    template_name = "djf_surveys/admin/question_list.html"
    success_url = reverse_lazy("djf_surveys:index")

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        self.object = self.get_object()
        if form.is_valid():
            form.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


@method_decorator(is_admin_or_org_admin, name="dispatch")
class SummaryResponseSurveyView(ContextTitleMixin, DetailView):
    model = Survey
    template_name = "djf_surveys/admins/summary.html"
    title_page = _("Summary")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        summary = SummaryResponse(survey=self.get_object())
        context["summary"] = summary
        return context


@method_decorator(is_admin_or_org_admin, name="dispatch")
class CreateSurveyQuestionFormView(ContextTitleMixin, SurveyFormView):
    model = OrgSurvey
    form_class = OrgAdminCreateSurveyForm
    title_page = _("Add Survey")
    survey = None

    def dispatch(self, request, *args, **kwargs):
        self.survey = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(survey=self.get_object(), user=self.request.user, **self.get_form_kwargs())

    def get_title_page(self):
        return self.get_object().name

    def get_sub_title_page(self):
        return self.get_object().description

    def get_context_data(self, *args, **kwargs):
        context = super(CreateSurveyQuestionFormView, self).get_context_data(*args, **kwargs)
        context["segment"] = "administrator"
        context["survey"] = self.survey
        context["organization"] = get_user_org(self.request.user)
        context["organization_pk"] = get_user_org(self.request.user).pk
        context["vendors"] = org_vendors(self.request.user)
        context["question"] = OrgQuestion.objects.filter(survey=self.survey)
        return context

    def get_success_url(self):
        url = reverse("djf_surveys:admin_edit_survey", args=[self.object.slug])
        return url


@method_decorator(is_admin_or_org_admin, name="dispatch")
class EditSurveyQuestionFormView(ContextTitleMixin, SurveyFormView):

    form_class = OrgAdminEditSurveyForm
    title_page = "Edit Survey"
    model = OrgUserAnswer
    survey = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_object().survey
        return context

    def dispatch(self, request, *args, **kwargs):
        # handle if user not same
        user_answer = self.get_object()
        self.survey = self.get_object().survey
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        user_answer = self.get_object()
        return form_class(user_answer=user_answer, **self.get_form_kwargs())

    def get_title_page(self):
        return self.get_object().survey.name

    def get_sub_title_page(self):
        return self.get_object().survey.description

    def get_context_data(self, *args, **kwargs):
        context = super(EditSurveyQuestionFormView, self).get_context_data(*args, **kwargs)
        context["segment"] = "administrator"
        context["survey"] = self.survey
        context["organization"] = get_user_org(self.request.user)
        context["vendors"] = org_vendors(self.request.user)
        context["organization_pk"] = get_user_org(self.request.user).pk
        context["question"] = OrgQuestion.objects.filter(survey=self.survey)
        context["activequestion"] = OrgQuestion.objects.filter(survey=self.survey, survey__active=True)
        return context

    def get_success_url(self):
        url = reverse("djf_surveys:admin_edit_survey", args=[self.object.survey.slug])
        return url


def import_questionnaire(request):
    if request.method == "POST":
        import_list = list(request.POST["import_list"].split(","))
        import_list = list(set(import_list))
        for i in import_list:
            header = ""
            survey = Survey.objects.filter(id=i)
            if survey.first().active == True:
                org_survey = OrgSurvey.objects.create(
                    org=get_user_org(request.user),
                    name=survey.first().name,
                    description=survey.first().description,
                    active=survey.first().active,
                    gracen_version=survey.first().gracen_version,
                    org_version=1.00,
                    gracen_survey=survey.first(),
                    user=request.user,
                    status=SurveyStatus.NOT_SENT,
                )
                questions = Question.objects.filter(survey=survey.first()).order_by("ordering")
                for q in questions:
                    prev_header = header
                    header = q.header
                    if header != prev_header:
                        QuestionHeader.objects.create(name=header)
                    org_question = OrgQuestion.objects.create(
                        org=get_user_org(request.user),
                        survey_id=org_survey.id,
                        label=q.label,
                        type_field=q.type_field,
                        choices=q.choices,
                        help_text=q.help_text,
                        required=q.required,
                        ordering=q.ordering,
                        header=q.header,
                    )
                    org_question.key = f"{get_user_org(request.user).pk}-{org_survey.pk}-{org_question.pk}"
                    org_question.save()
        return redirect("djf_surveys:admin_survey")


def update_admin_org_version(request, pk):
    OrgSurvey.objects.filter(pk=pk).update(org_version=request.POST.get("new_org_version"))
    return HttpResponse("Org admin version updated.")


def survey_import_details(request, pk):
    from apps.vendor.models import VendorSurvey

    survey_object = OrgSurvey.objects.filter(pk=pk).first()
    context = {}
    context["segment"] = "administrator"
    context["organization"] = get_user_org(request.user)
    context["organization_pk"] = get_user_org(request.user).pk
    context["object"] = survey_object
    vendor_survey = VendorSurvey.objects.filter(survey=survey_object)
    context["total_count"] = vendor_survey.distinct("vendor").count()
    search = request.GET.get("q", None)
    if search:
        vendor_survey = vendor_survey.filter(vendor__name__icontains=search)
    context["surveys"] = vendor_survey
    return render(request, "djf_surveys/admin/import_details.html", context=context)


def view_question_document(request, pk):
    answer = OrgAnswer.objects.filter(question__pk=pk).first()
    if not answer:
        return HttpResponseRedirect(request.META.get("HTTP_REFERER"))
    with default_storage.open(answer.document.name, "rb") as file:
        mime_type, _ = mimetypes.guess_type(answer.document.name)
        response = HttpResponse(file.read(), content_type=mime_type)
        response["Content-Disposition"] = f'inline; filename="{answer.question.label}"'
        return response
