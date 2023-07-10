import csv
from io import StringIO

from django.utils.text import capfirst
from django.utils.translation import gettext, gettext_lazy as _
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormMixin
from django.utils.decorators import method_decorator

# from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse, reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View
from django.http import JsonResponse, HttpResponse
from django.contrib import messages

from apps.djf_surveys.app_settings import SURVEYS_ADMIN_BASE_PATH
from apps.djf_surveys.models import Survey, Question, UserAnswer, OrgSurvey, QuestionHeader
from apps.djf_surveys.mixin import ContextTitleMixin
from apps.djf_surveys.views import SurveyListView
from apps.djf_surveys.forms import BaseSurveyForm, AdminCreateSurveyForm, AdminEditSurveyForm
from apps.djf_surveys.summary import SummaryResponse
from apps.vendor.views import get_user_org
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Max
import pandas as pd
from apps.djf_surveys.models import generate_unique_slug
import math
from .tables import SurveyTable


@method_decorator(staff_member_required, name="dispatch")
class AdminCrateSurveyView(ContextTitleMixin, CreateView):
    model = Survey
    template_name = "djf_surveys/gracen_admin/survey_form.html"
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
            survey.gracen_version = 1.00
            survey.save()
            self.success_url = reverse("djf_surveys:gracen_admin_edit_survey", args=[survey.slug])
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, *args, **kwargs):
        context = super(AdminCrateSurveyView, self).get_context_data(*args, **kwargs)
        context["segment"] = "questionnaire"
        return context


@method_decorator(staff_member_required, name="dispatch")
class AdminEditSurveyView(ContextTitleMixin, UpdateView):
    model = Survey
    template_name = "djf_surveys/gracen_admin/survey_form.html"
    fields = [
        "name",
        "description",
        "active",
    ]
    title_page = _("Edit Survey")

    def get_success_url(self):
        return reverse("djf_surveys:gracen_admin_survey")

    def get_context_data(self, *args, **kwargs):
        context = super(AdminEditSurveyView, self).get_context_data(*args, **kwargs)
        answer = UserAnswer.objects.filter(user=self.request.user, survey=self.object)
        if answer.exists():
            self.object.answer = answer.first()
        else:
            self.object.answer = None
        context["segment"] = "questionnaire"
        context["question"] = Question.objects.filter(survey=self.object)
        return context


@method_decorator(staff_member_required, name="dispatch")
class AdminSurveyListView(SurveyListView):
    template_name = "administrator/gracen/liabrary_list.html"

    def get_context_data(self, *args, **kwargs):
        context = super(AdminSurveyListView, self).get_context_data(*args, **kwargs)
        context["segment"] = "questionnaire"
        return context


@staff_member_required
def surveys(request):
    sort = request.GET.get("sort", "name")
    page = request.GET.get("page", 1)
    page_size = request.GET.get("page_size", 15)
    search = request.GET.get("search", "")
    surveys = Survey.objects.all()
    if search:
        surveys = surveys.filter(name__icontains=search)
    table = SurveyTable(data=surveys, order_by=sort)
    total_data = surveys.count()
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
        "segment": "questionnaire",
        "tabledata": table,
    }
    return render(request, "administrator/gracen/liabrary_list.html", context)


@method_decorator(staff_member_required, name="dispatch")
class AdminSurveyFormView(ContextTitleMixin, FormMixin, DetailView):
    model = Survey
    template_name = "djf_surveys/gracen_admin/survey_form.html"
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
        context["questions"] = Question.objects.filter(survey=self.object).order_by("ordering")
        context["segment"] = "questionnaire"
        return context


@method_decorator(staff_member_required, name="dispatch")
class AdminDeleteSurveyView(DetailView):
    model = Survey

    def get(self, request, *args, **kwargs):
        survey = self.get_object()
        survey.delete()
        return redirect("djf_surveys:gracen_admin_survey")


@method_decorator(staff_member_required, name="dispatch")
class AdminQuestionFormView(ContextTitleMixin, FormMixin, DetailView):
    model = Survey
    template_name = "djf_surveys/gracen_admin/question_preview.html"
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
        context = super(AdminQuestionFormView, self).get_context_data(*args, **kwargs)
        context["question"] = Question.objects.filter(survey=self.object).order_by("ordering")
        context["segment"] = "questionnaire"
        return context


@method_decorator(staff_member_required, name="dispatch")
class AdminCreateQuestionView(ContextTitleMixin, CreateView):
    model = Question
    template_name = "djf_surveys/gracen_admin/questions_form.html"
    success_url = reverse_lazy("djf_surveys:")
    fields = ["label", "key", "type_field", "choices", "help_text", "required"]
    title_page = _("Add Question")
    survey = None

    def dispatch(self, request, *args, **kwargs):
        self.survey = get_object_or_404(Survey, id=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            total_question = Question.objects.filter(survey=self.survey).aggregate(Max("ordering"))["ordering__max"]
            question = form.save(commit=False)
            question.survey = self.survey
            question.ordering = total_question + 1 if total_question else 1
            question.save()
            prev_question = Question.objects.filter(ordering=question.ordering-1,
                                                    survey=self.survey)
            if prev_question:
                question.header = prev_question.first().header
            question.key = f"{self.survey.id}-{question.id}"
            question.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse("djf_surveys:gracen_admin_question_list", args=[self.survey.pk]) + "?Redirect=true"

    def get_context_data(self, *args, **kwargs):
        context = super(AdminCreateQuestionView, self).get_context_data(*args, **kwargs)
        context["segment"] = "questionnaire"
        context["survey"] = self.survey
        return context


@method_decorator(staff_member_required, name="dispatch")
class AdminUpdateQuestionView(ContextTitleMixin, UpdateView):
    model = Question
    template_name = "djf_surveys/gracen_admin/questions_form.html"
    success_url = "gracen_admin_home"
    fields = ["label", "key", "type_field", "choices", "help_text", "required"]
    title_page = _("Add Question")
    survey = None

    def dispatch(self, request, *args, **kwargs):
        question = self.get_object()
        self.survey = question.survey
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        if self.model.id:
            return reverse("djf_surveys:gracen_admin_question_list", args=[self.survey.id])
        else:
            return reverse("djf_surveys:gracen_admin_edit_survey", args=[self.survey.slug])

    def get_context_data(self, *args, **kwargs):
        context = super(AdminUpdateQuestionView, self).get_context_data(*args, **kwargs)
        context["segment"] = "questionnaire"
        context["survey"] = self.survey
        return context


@method_decorator(staff_member_required, name="dispatch")
class AdminDeleteQuestionView(DetailView):
    model = Question
    survey = None

    def dispatch(self, request, *args, **kwargs):
        question = self.get_object()
        self.survey = question.survey
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        question = self.get_object()
        question.delete()
        return redirect("djf_surveys:gracen_admin_question_list", pk=self.survey.id)


@method_decorator(staff_member_required, name="dispatch")
class AdminChangeOrderQuestionView(View):
    def post(self, request, *args, **kwargs):
        ordering = request.POST["order_question"].split(",")
        ordering = [i for i in ordering if i != ""]
        order_question_id = request.POST["order_question_id"]
        on_header = request.POST["on_header"]
        question_object = Question.objects.filter(pk=order_question_id)
        header_object = question_object.first().header
        survey_questions = Question.objects.filter(survey=question_object.first().survey).order_by("ordering")

        for index, question_id in enumerate(ordering):
            if question_id:
                question = Question.objects.get(id=question_id)
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


@method_decorator(staff_member_required, name="dispatch")
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


@method_decorator(staff_member_required, name="dispatch")
class SummaryResponseSurveyView(ContextTitleMixin, DetailView):
    model = Survey
    template_name = "djf_surveys/admins/summary.html"
    title_page = _("Summary")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        summary = SummaryResponse(survey=self.get_object())
        context["summary"] = summary
        return context


class SurveyFormView(FormMixin, DetailView):
    template_name = "djf_surveys/gracen_admin/question_list.html"
    success_url = reverse_lazy("djf_surveys:index")

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        self.object = self.get_object()
        if form.is_valid():
            form.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


@method_decorator(staff_member_required, name="dispatch")
class CreateSurveyQuestionFormView(ContextTitleMixin, SurveyFormView):
    model = Survey
    form_class = AdminCreateSurveyForm
    # success_url = reverse_lazy("djf_surveys:index")
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
        context["segment"] = "questionnaire"
        context["survey"] = self.survey
        context["question"] = Question.objects.filter(survey=self.survey)
        return context

    def get_success_url(self):
        url = reverse("djf_surveys:gracen_admin_edit_survey", args=[self.object.slug])
        return url


@method_decorator(staff_member_required, name="dispatch")
class EditSurveyQuestionFormView(ContextTitleMixin, SurveyFormView):

    form_class = AdminEditSurveyForm
    title_page = "Edit Survey"
    model = UserAnswer
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
        context["segment"] = "questionnaire"
        context["survey"] = self.survey
        return context

    def get_success_url(self):
        url = reverse("djf_surveys:gracen_admin_edit_survey", args=[self.object.survey.slug])
        return url


def update_gracen_version(request, pk):
    Survey.objects.filter(pk=pk).update(gracen_version=request.POST.get("new_grc_version"))
    return HttpResponse("gracen_admin_version_updated")


def survey_import_details(request, pk):

    survey_object = Survey.objects.filter(pk=pk).first()
    context = {}
    context["segment"] = "questionnaire"
    context["object"] = survey_object
    org_survey = OrgSurvey.objects.filter(gracen_survey=survey_object)
    context["total_count"] = org_survey.distinct("org").count()
    search = request.GET.get("q", None)
    if search:
        org_survey = org_survey.filter(org__name__icontains=search)
    context["surveys"] = org_survey
    return render(request, "djf_surveys/gracen_admin/import_details.html", context=context)


def get_question_type(type):
    question_type = {
        "text": 0,
        "number": 1,
        "radio": 2,
        "select": 3,
        "multi_select": 4,
        "text_area": 5,
        "url": 6,
        "email": 7,
        "date": 8,
        "rating": 9,
        "document": 10,
        "yes-no-n/a": 11,
    }
    return question_type[type]


def import_survey(request):
    context = {}
    if request.method == "POST":
        error = False
        try:
            myfile = request.FILES["file"]
            file_data = pd.read_excel(myfile)
            file_data.fillna("", inplace=True)
            question_list = []
            name = file_data.columns[0]
            question_list = []
            if not name:
                error = True
                messages.error(request, "Name is not placed in right position")
            description = file_data.iloc[0][0]
            if not description:
                error = True
                messages.error(request, "Description is not placed in right position")
            survey_obj = Survey(name=name, description=description, gracen_version=1.0, active=False)
            for index, row in file_data[3:].iterrows():
                if not row[0]:
                    error = True
                    messages.error(request, "Please start adding your question after header.")
                    break
                if not row[1]:
                    error = True
                    messages.error(request, f"Question no. {index-2} must have help text")
                type = row[2].lower()
                if not type:
                    error = True
                    messages.error(request, f"Question no. {index-2} must have type")
                elif type in ["radio", "select", "multi select"]:
                    choices = row[3].strip(",").split(",")
                    if len(choices) < 2:
                        error = True
                        messages.error(
                            request,
                            f"Question no. {index-2} Type {type} choices values must present in comma separated",
                        )
                if type == "yes-no-n/a":
                    choices = "Yes,No,N/A".strip(",")
                else:
                    choices = row[3].strip(",")
                type = get_question_type(type.replace(" ", "_"))
                if row[4] not in ["T", "F"]:
                    error = True
                    messages.error(request, "Question must have required field either T or F")
                question = Question(
                    survey=survey_obj,
                    label=row[0],
                    help_text=row[1],
                    type_field=type,
                    choices=choices,
                    required=True if row[4] == "T" else False,
                    ordering=index - 2,
                )
                question.key = generate_unique_slug(Question, row[0], question.id, "key")
                question_list.append(question)
            if not error:
                survey_obj.save()
                Question.objects.bulk_create(question_list)
                context["success"] = True
                context["survey"] = survey_obj.slug
            else:
                context["error"] = error
        except Exception as e:
            messages.error(request, "Something went wrong. Please check your file.")
            context["error"] = error
            return render(request, "djf_surveys/gracen_admin/import_survey.html", context)
    return render(request, "djf_surveys/gracen_admin/import_survey.html", context)
