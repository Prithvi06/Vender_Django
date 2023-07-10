import mimetypes
from django.urls import reverse_lazy, reverse
from django.utils.text import capfirst
from django.utils.translation import gettext, gettext_lazy as _
from django.views.generic.list import ListView
from django.views.generic.edit import FormMixin
from django.views.generic.detail import DetailView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import redirect
from django.contrib import messages
from django.core.files.storage import default_storage
from apps.djf_surveys.models import Survey, UserAnswer, OrgSurvey, get_type_field_display, SurveyStatus
from apps.djf_surveys.forms import CreateSurveyForm, EditSurveyForm
from apps.djf_surveys.mixin import ContextTitleMixin
from apps.djf_surveys import app_settings
from apps.djf_surveys.utils import NewPaginator
from apps.vendor.views import get_user_org
from django.views.generic import View
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.views.generic.edit import CreateView, UpdateView
from apps.vendor.models import (
    VendorSurveyQuestion,
    VendorSurvey,
    HistoricalVendorSurveyQuestion,
    HistoricalVendorSurveyAnswer,
    VendorSurveyUserAnswer,
    SurveyToken,
    VendorSurveyAnswer,
)
from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect
from itertools import chain
from pytz import timezone as time_zone
from organizations.models import OrganizationUser
from apps.djf_surveys.models import Question, OrgQuestion, QuestionHeader
from datetime import date
from django.views.decorators.cache import cache_control
from django.utils import timezone
from django.db.models import Q


@method_decorator(login_required, name="dispatch")
class SurveyListView(ContextTitleMixin, ListView):
    model = Survey
    title_page = "Survey List"
    paginate_by = app_settings.SURVEY_PAGINATION_NUMBER["survey_list"]
    paginator_class = NewPaginator

    def get_queryset(self):
        query = self.request.GET.get("q")
        if query:
            object_list = self.model.objects.filter(name__icontains=query)
        else:
            object_list = self.model.objects.all()
        return object_list

    def get_context_data(self, **kwargs):
        page_number = self.request.GET.get("page", 1)
        context = super().get_context_data(**kwargs)
        page_range = context["page_obj"].paginator.get_elided_page_range(number=page_number)
        context["page_range"] = page_range
        return context


@method_decorator(login_required, name="dispatch")
class OrgSurveyListView(ContextTitleMixin, ListView):
    model = OrgSurvey
    title_page = "Survey List"
    paginate_by = app_settings.SURVEY_PAGINATION_NUMBER["survey_list"]
    paginator_class = NewPaginator

    def get_queryset(self):
        query = self.request.GET.get("q")
        if query:
            object_list = self.model.objects.filter(name__icontains=query, org=get_user_org(self.request.user))
        else:
            object_list = self.model.objects.filter(org=get_user_org(self.request.user))
        return object_list

    def get_context_data(self, **kwargs):
        page_number = self.request.GET.get("page", 1)
        context = super().get_context_data(**kwargs)
        page_range = context["page_obj"].paginator.get_elided_page_range(number=page_number)
        context["page_range"] = page_range
        return context


class SurveyFormView(FormMixin, DetailView):
    template_name = "djf_surveys/survey_form.html"
    success_url = reverse_lazy("djf_surveys:index")

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        self.object = self.get_object()
        if form.is_valid():
            form.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    # def get_success_url(self):
    #     return reverse("djf_surveys:admin_survey")


class CreateSurveyFormView(ContextTitleMixin, SurveyFormView):

    model = VendorSurvey
    form_class = CreateSurveyForm
    # success_url = reverse_lazy("djf_surveys:index")
    title_page = _("Add Survey")
    survey = None

    def dispatch(self, request, *args, **kwargs):

        self.survey = self.get_object()
        if not request.user.is_authenticated:
            return reverse("djf_surveys:index")
        answer = VendorSurveyUserAnswer.objects.filter(
            vendor_id=self.survey.vendor.pk,
            survey=self.survey
        )
        if answer.exists():
            return redirect(reverse("djf_surveys:edit", args=[answer.first().pk]))
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        self.object = self.get_object()
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(survey=self.get_object(),
                          user=self.request.user,
                          **self.get_form_kwargs(),
                          name=self.request.user.first_name + " " + self.request.user.last_name 
                          )

    def get_title_page(self):
        return self.get_object().name

    def get_sub_title_page(self):
        return self.get_object().description

    def get_context_data(self, *args, **kwargs):
        context = super(CreateSurveyFormView, self).get_context_data(*args, **kwargs)
        context["segment"] = "vendors"
        context["survey_question"] = VendorSurveyQuestion.objects.filter(survey=self.survey, is_deleted=False).first()
        context["organization"] = get_user_org(self.request.user)
        context["organization_pk"] = get_user_org(self.request.user).pk
        context["users"] = self.survey.vendor.contact_set.all().exclude(Q(is_deleted=True) | Q(email=None))
        return context

    def get_success_url(self):
        url = reverse("vendor-edit", args=[self.object.vendor.pk])
        url = url + "?section=QUESTIONS"
        return url


def get_history(id, user, vendor):
    history_object = HistoricalVendorSurveyQuestion.objects.filter(survey_id=id).order_by("history_date")
    user_answer = VendorSurveyUserAnswer.objects.filter(survey_id=id, vendor=vendor)
    answer_history = []
    if user_answer.exists():
        answer_history = HistoricalVendorSurveyAnswer.objects.filter(user_answer=user_answer.first()).order_by(
            "history_date"
        )
    history_object = sorted(chain(history_object, answer_history), key=lambda instance: instance.history_date)
    history_str = ""
    all_question = list(
        VendorSurveyQuestion.objects.filter(survey_id=id, vendor=vendor, is_deleted=False)
        .order_by("ordering")
        .values_list("id", flat=True)
    )
    next_data = []
    new_history = history_object
    for data in new_history:
        # ques_deleted = False
        if not data.__class__.__name__ == "HistoricalVendorSurveyQuestion":
            if data.get_history_type_display() == "Changed":
                break
            author = ""
            label_char = "."
            if len(data.question.label) > 50:
                label_char = "..."

            try:
                index = all_question.index(data.question.id) + 1
                question_label = f"<span>{index}) {data.question.label[:50]}{label_char}</span>"
            except:
                index = -1
                question_label = f"<span>(DELETED QUESTION) {data.question.label[:50]}{label_char}</span>"
            author = (f"{data.name}").capitalize()
            history_str_ = f"<h6 class='mb-0 mt-2' style='color:black;font-size:0.75rem!important'>{str(data.history_date.astimezone(time_zone('US/Pacific')).strftime('%m/%d/%y %I:%M %p'))} - {author}</h6>{question_label}"
            if data.value:
                history_str = history_str + history_str_
                pre_value = ""
                value = data.value
                history_str = history_str + "<span class='history-text'> {} <span style='font-weight:bold'>--></span>  {}</span>".format(
                    pre_value,
                    value,
                )
            elif data.document:
                history_str = history_str + history_str_
                history_str = history_str + "<h5 class='history-text'><span style='text-decoration:underline'>{}</span>:  File Changed</h5>".format(
                    ("Document").replace("_", " ").capitalize(),
                )
            elif data.na_explain:
                history_str = history_str + history_str_
                pre_value = ""
                value = data.na_explain
                history_str = history_str + "<h5 class='history-text'><span style='text-decoration:underline'>{}</span>: {}  <span style='font-weight:bold'>--></span>  {}</h5>".format(
                    ("na_explain").replace("_", " ").capitalize(),
                    pre_value,
                    value,
                )
    for data in history_object:
        if data.next_record:
            delta = data.next_record.diff_against(data)
            key = False
            author = ""
            ques_deleted = False
            if delta.changes:
                question_label = ""
                if data.__class__.__name__ == "HistoricalVendorSurveyQuestion":

                    if data.next_record.history_user:
                        author = data.next_record.history_user.first_name + " " + data.next_record.history_user.last_name
                    if delta.changes[0].field == "key":
                        key = True
                    label_char = "."
                    if len(data.next_record.label) > 50:
                        label_char = "..."
                    try:
                        index = all_question.index(data.next_record.id) + 1
                        question_label = f"<span>{index}) {data.next_record.label[:50]}{label_char}</span>"
                    except:
                        index = -1
                        ques_deleted = data.next_record.is_deleted
                        question_label = f"<span>(DELETED QUESTION) {data.next_record.label[:50]}{label_char}</span>"
                else:
                    author = data.next_record.name
                    next_data.append(data.next_record.question.id)
                    label_char = "."
                    if len(data.next_record.question.label) > 50:
                        label_char = "..."
                    try:
                        index = all_question.index(data.next_record.question.id) + 1
                        question_label = f"<span>{index}) {data.next_record.question.label[:50]}{label_char}</span>"
                    except:
                        index = -1
                        ques_deleted = False
                        question_label = f"<span>(DELETED QUESTION) {data.next_record.question.label[:50]}{label_char}</span>"
                        
                if not key:
                    author = author.capitalize() if author else ''
                    if not ques_deleted:
                        history_str = (
                            history_str
                            + f"<h6 class='mb-0 mt-2' style='color:black; font-size:0.75rem!important'>{str(data.next_record.history_date.astimezone(time_zone('US/Pacific')).strftime('%m/%d/%y %I:%M %p'))} - {author}</h6>{question_label}"
                        )
                    else:
                        history_str = (
                            history_str
                            + f"<h6 class='mb-0 mt-2' style='color:black; font-size:0.75rem!important'>{str(data.next_record.history_date.astimezone(time_zone('US/Pacific')).strftime('%m/%d/%y %I:%M %p'))} - {author}</h6>"
                        )
                for change in delta.changes:
                    if data.__class__.__name__ == "HistoricalVendorSurveyQuestion":
                        if change.field in ["type_field"]:
                            pre_value = get_type_field_display(change.old)
                            value = get_type_field_display(change.new)
                        elif change.field == "required":
                            pre_value = "Yes" if change.old else "No"
                            value = "Yes" if change.new else "No"
                        elif change.field == "is_deleted":
                            pre_value = "DELETED QUESTION"
                            value = data.label
                        else:
                            pre_value = str(change.old).strip() if change.old else ""
                            value = str(change.new).strip() if change.new else ""
                        if change.field == "is_deleted":
                            history_str = history_str + "<h5 class='history-text'>{}  <span style='font-weight:bold'>--></span>  {}</h5>".format(
                                pre_value,
                                value,
                            )
                        else:
                            if change.field != "key":
                                history_str = history_str + "<h5 class='history-text'><span style='text-decoration:underline'>{}</span>: {}  <span style='font-weight:bold'>--></span>  {}</h5>".format(
                                    (change.field).replace("_", " ").capitalize(),
                                    pre_value,
                                    value,
                                )
                    else:
                        if change.field == "value":
                            pre_value = str(change.old).strip() if change.old else ""
                            value = str(change.new).strip() if change.new else ""
                            history_str = history_str + "<span class='history-text'> {} <span style='font-weight:bold'>--></span>  {}</span>".format(
                                pre_value,
                                value,
                            )
                        elif change.field == "document":
                            history_str = history_str + "<h5 class='history-text'><span style='text-decoration:underline'>{}</span>:  File Changed</h5>".format(
                                (change.field).replace("_", " ").capitalize(),
                            )
                        elif change.field == "na_explain":
                            pre_value = str(change.old).strip() if change.old else ""
                            value = str(change.new).strip() if change.new else ""
                            history_str = history_str + "<h5 class='history-text'><span style='text-decoration:underline'>{}</span>: {}  <span style='font-weight:bold'>--></span>  {}</h5>".format(
                                (change.field).replace("_", " ").capitalize(),
                                pre_value,
                                value,
                            )
    return history_str


@method_decorator(login_required, name="dispatch")
class EditSurveyFormView(ContextTitleMixin, SurveyFormView):

    form_class = EditSurveyForm
    title_page = "Edit Survey"
    model = VendorSurveyUserAnswer
    survey = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_object().survey
        return context

    def dispatch(self, request, *args, **kwargs):
        # handle if user not same
        user_answer = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        self.object = self.get_object()
        if form_class is None:
            form_class = self.get_form_class()
        user_answer = self.get_object()
        return form_class(user_answer=user_answer,
                          **self.get_form_kwargs(),
                          user=self.request.user,
                          name=self.request.user.first_name + " " + self.request.user.last_name
                          )

    def get_title_page(self):
        return self.get_object().survey.name

    def get_sub_title_page(self):
        return self.get_object().survey.description

    def get_context_data(self, *args, **kwargs):
        context = super(EditSurveyFormView, self).get_context_data(*args, **kwargs)
        context["segment"] = "vendors"
        context["show_history"] = True
        context["edit_survey"] = self.object.survey
        context["survey_question"] = VendorSurveyQuestion.objects.filter(
            survey=self.object.survey, is_deleted=False
        ).first()
        context["organization"] = get_user_org(self.request.user)
        context["organization_pk"] = get_user_org(self.request.user).pk
        context["history"] = get_history(self.object.survey, self.request.user, self.object.survey.vendor)
        context["users"] = self.object.survey.vendor.contact_set.all().exclude(Q(is_deleted=True) | Q(email=None))
        return context

    def get_success_url(self):
        url = reverse("vendor-edit", args=[self.object.survey.vendor.pk])
        url = url + "?section=QUESTIONS"
        return url


@method_decorator(login_required, name="dispatch")
class DeleteSurveyAnswerView(DetailView):
    model = UserAnswer

    def dispatch(self, request, *args, **kwargs):
        # handle if user not same
        user_answer = self.get_object()
        if user_answer.user != request.user:
            messages.warning(request, gettext("You can't delete this survey. You don't have permission."))
            return reverse("djf_surveys:index")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        user_answer = self.get_object()
        user_answer.delete()
        messages.success(self.request, gettext("Answer succesfully deleted."))
        return redirect("djf_surveys:detail", slug=user_answer.survey.slug)


class DetailSurveyView(ContextTitleMixin, DetailView):
    model = Survey
    template_name = "djf_surveys/answer_list.html"
    title_page = "Survey Detail"
    paginate_by = app_settings.SURVEY_PAGINATION_NUMBER["answer_list"]

    def dispatch(self, request, *args, **kwargs):
        survey = self.get_object()
        if not self.request.user.is_superuser:
            messages.warning(request, gettext("You can't access this page. You don't have permission."))
            return reverse("djf_surveys:index")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        user_answers = (
            UserAnswer.objects.filter(survey=self.get_object())
            .select_related("user")
            .prefetch_related("answer_set__question")
        )
        paginator = NewPaginator(user_answers, self.paginate_by)
        page_number = self.request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        page_range = paginator.get_elided_page_range(number=page_number)
        context = super().get_context_data(**kwargs)
        context["page_obj"] = page_obj
        context["page_range"] = page_range
        return context


@method_decorator(login_required, name="dispatch")
class DetailResultSurveyView(ContextTitleMixin, DetailView):
    title_page = _("Survey Result")
    template_name = "djf_surveys/detail_result.html"
    model = UserAnswer

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_object()
        context["on_detail"] = True
        return context

    def dispatch(self, request, *args, **kwargs):
        # handle if user not same
        user_answer = self.get_object()
        if user_answer.user != request.user:
            messages.warning(request, gettext("You can't access this page. You don't have permission."))
            return reverse("djf_surveys:index")
        return super().dispatch(request, *args, **kwargs)

    def get_title_page(self):
        return self.get_object().survey.name

    def get_sub_title_page(self):
        return self.get_object().survey.description


@method_decorator(login_required, name="dispatch")
class VendorCreateQuestionView(ContextTitleMixin, CreateView):
    model = VendorSurveyQuestion
    template_name = "djf_surveys/question_form.html"
    success_url = reverse_lazy("djf_surveys:")
    fields = ["label", "key", "type_field", "choices", "help_text", "required"]
    title_page = _("Add Question")
    survey = None

    def dispatch(self, request, *args, **kwargs):
        self.survey = get_object_or_404(Survey, id=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        question = VendorSurveyQuestion.objects.filter(key=request.POST["key"])
        if question.exists():
            context = {}
            context["segment"] = "vendor"
            context["error"] = "Key must be unique."
            context["survey"] = self.survey
            return render(request, "djf_surveys/question_form.html", context)
        form = self.get_form()
        if form.is_valid():
            question = form.save(commit=False)
            question.survey = self.survey
            question.save()
            history = question.history.filter(pk=question.history.latest().pk).update(history_user=request.user)
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse("djf_surveys:question_list", args=[self.survey.pk])

    def get_context_data(self, *args, **kwargs):
        context = super(VendorCreateQuestionView, self).get_context_data(*args, **kwargs)
        context["segment"] = "vendor"
        context["survey"] = self.survey
        return context


@method_decorator(login_required, name="dispatch")
class VendorUpdateQuestionView(ContextTitleMixin, UpdateView):
    model = VendorSurveyQuestion
    template_name = "djf_surveys/question_form.html"
    success_url = "gracen_admin_home"
    fields = ["label", "key", "type_field", "choices", "help_text", "required"]
    title_page = _("Add Question")
    survey = None

    def form_valid(self, form):
        question = form.save()
        question.history.filter(pk=question.history.latest().pk).update(history_user=self.request.user)
        return HttpResponseRedirect(self.get_success_url())

    def dispatch(self, request, *args, **kwargs):
        question = self.get_object()
        self.survey = question.survey
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        answer = VendorSurveyUserAnswer.objects.filter(vendor=self.survey.vendor, survey_id=self.survey.pk)
        if answer.exists():
            return reverse("djf_surveys:edit", args=[answer.first().pk])
        else:
            return reverse("djf_surveys:create", args=[self.survey.slug])

    def get_context_data(self, *args, **kwargs):
        context = super(VendorUpdateQuestionView, self).get_context_data(*args, **kwargs)
        answer = VendorSurveyUserAnswer.objects.filter(vendor=self.survey.vendor, survey_id=self.survey.pk)
        context["answer"] = None
        if answer.exists():
            context["answer"] = answer.first()
        context["segment"] = "vendors"
        context["survey"] = self.survey
        context["organization"] = get_user_org(self.request.user)
        context["organization_pk"] = get_user_org(self.request.user).pk
        return context


@method_decorator(login_required, name="dispatch")
class VendorDeleteQuestionView(DetailView):
    model = VendorSurveyQuestion
    survey = None

    def dispatch(self, request, *args, **kwargs):
        question = self.get_object()
        self.survey = question.survey
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        question = self.get_object()
        question.is_deleted = True
        question.save()
        question.history.filter(pk=question.history.latest().pk).update(history_user=self.request.user)
        answer = VendorSurveyUserAnswer.objects.filter(vendor=self.survey.vendor, survey_id=self.survey.pk)
        if answer.exists():
            return redirect("djf_surveys:edit", pk=answer.first().id)
        else:
            return redirect("djf_surveys:create", slug=self.survey.slug)


@method_decorator(login_required, name="dispatch")
class VendorChangeOrderQuestionView(View):
    def post(self, request, *args, **kwargs):
        ordering = request.POST["order_question"].split(",")
        ordering = [i for i in ordering if i != ""]
        order_question_id = request.POST["order_question_id"]
        on_header = request.POST["on_header"]
        question_object = VendorSurveyQuestion.objects.filter(pk=order_question_id)
        header_object = question_object.first().header
        survey_questions = VendorSurveyQuestion.objects.filter(survey=question_object.first().survey).order_by(
            "ordering"
        )
        for index, question_id in enumerate(ordering):
            if question_id:
                question = VendorSurveyQuestion.objects.get(id=question_id)
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
                question.history.filter(pk=question.history.latest().pk).update(history_user=request.user)
        data = {"message": gettext("Update ordering of questions succeeded.")}
        return JsonResponse(data, status=200)


class VendorSurveyFormView(FormMixin, DetailView):
    template_name = "djf_surveys/vendor_survey_form.html"
    # success_url = reverse_lazy("djf_surveys:index")

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        self.object = self.get_object()
        if form.is_valid():
            form.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


class VendorCreateSurveyFormView(ContextTitleMixin, VendorSurveyFormView):

    model = VendorSurvey
    form_class = CreateSurveyForm
    # success_url = reverse_lazy("djf_surveys:index")
    title_page = _("Add Survey")
    survey = None

    def dispatch(self, request, *args, **kwargs):

        survey = self.get_object()
        if not request.user.is_authenticated:
            return reverse("login")

        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        if form_class is None:
            form_class = self.get_form_class()
        return form_class(survey=self.get_object(), user=self.request.user, **self.get_form_kwargs())

    def get_context_data(self, *args, **kwargs):
        context = super(VendorCreateSurveyFormView, self).get_context_data(*args, **kwargs)
        context["segment"] = "questionnaire"
        context["vendor"] = self.object.vendor
        return context

    def get_success_url(self):
        url = reverse("vendor_surveys", args=[self.object.vendor.pk])
        return url


@method_decorator(login_required, name="dispatch")
class VendorEditSurveyFormView(ContextTitleMixin, VendorSurveyFormView):

    form_class = EditSurveyForm
    title_page = "Edit Survey"
    model = VendorSurveyUserAnswer
    survey = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_object().survey
        return context

    def dispatch(self, request, *args, **kwargs):
        # handle if user not same
        user_answer = self.get_object()
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
        context = super(VendorEditSurveyFormView, self).get_context_data(*args, **kwargs)
        context["segment"] = "questionnaire"
        context["show_history"] = True
        context["edit_survey"] = self.object.survey
        context["vendor"] = self.object.survey.vendor
        return context

    def get_success_url(self):
        url = reverse("vendor_surveys", args=[self.object.survey.vendor.pk])
        return url


class InviteSurveyFormView(FormMixin, DetailView):

    template_name = "djf_surveys/vendor_question_form.html"
    success_url = reverse_lazy("djf_surveys:index")

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        self.object = self.get_object()
        if form.is_valid():
            form.save()
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


@method_decorator(cache_control(no_cache=True, must_revalidate=True, no_store=True), name="dispatch")
@method_decorator(login_required(login_url="account_login"), name="dispatch")
class InviteCreateSurveyFormView(ContextTitleMixin, InviteSurveyFormView):

    model = VendorSurvey
    form_class = CreateSurveyForm
    title_page = _("Add Survey")
    survey = None

    def dispatch(self, request, *args, **kwargs):

        survey = self.get_object()
        if not request.user.is_authenticated:
            return reverse("djf_surveys:index")
        token_object = SurveyToken.objects.filter(
            key=self.kwargs["token"],
            user=request.user,
            expiration_date__date__gte=date.today(),
            survey=survey,
        )
        if not token_object:
            return render(request, "registration/survey_login.html", {"token": False})

        user_answer = VendorSurveyUserAnswer.objects.filter(
            vendor_id=survey.vendor.pk,
            survey=survey
        )
        if user_answer.exists():
            return redirect(reverse("djf_surveys:invite-survey-edit", args=[self.kwargs["token"], user_answer.first().pk]))
    
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        if form_class is None:
            obj = self.get_object()
            if obj.status not in [SurveyStatus.IN_PROGRESS, SurveyStatus.IN_REVIEW]:
                obj.status = SurveyStatus.VIEWED
                obj.save()
            form_class = self.get_form_class()
        return form_class(
            survey=self.get_object(),
            user=self.request.user,
            temp=True,
            **self.get_form_kwargs(),
            token=self.kwargs["token"],
            is_invite=True,
            name=self.request.user.first_name + " " + self.request.user.last_name
        )

    def get_title_page(self):
        return self.get_object().name

    def get_sub_title_page(self):
        return self.get_object().description

    def get_context_data(self, *args, **kwargs):
        self.object.last_activity = timezone.now()
        self.object.save()
        context = super(InviteCreateSurveyFormView, self).get_context_data(*args, **kwargs)
        context["survey_question"] = VendorSurveyQuestion.objects.filter(survey=self.get_object(), is_deleted=False).first()
        context["organization"] = get_user_org(self.request.user)
        context["token"] = self.kwargs["token"]
        return context

    def get_success_url(self):
        action_name = self.request.POST.get("action")
        url = reverse("djf_surveys:invite_questionnarie_redirect", args=[self.kwargs["token"]])
        url = url + f"?action={action_name}"
        return url


@method_decorator(cache_control(no_cache=True, must_revalidate=True, no_store=True), name="dispatch")
@method_decorator(login_required(login_url="account_login"), name="dispatch")
class InviteEditSurveyFormView(ContextTitleMixin, InviteSurveyFormView):

    form_class = EditSurveyForm
    title_page = "Edit Survey"
    model = VendorSurveyUserAnswer
    survey = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_object().survey
        return context

    def dispatch(self, request, *args, **kwargs):
        # handle if user not same
        token_object = SurveyToken.objects.filter(
            key=self.kwargs["token"],
            user=request.user,
            expiration_date__date__gte=date.today(),
            survey=self.get_object().survey,
        )
        if not token_object:
            return render(request, "registration/survey_login.html", {"token": False})
        user_answer = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        if form_class is None:
            obj = self.get_object().survey
            if obj.status not in [SurveyStatus.IN_PROGRESS, SurveyStatus.IN_REVIEW]:
                obj.status = SurveyStatus.VIEWED
                obj.save()
            form_class = self.get_form_class()
        user_answer = self.get_object()
        return form_class(
            user_answer=user_answer,
            **self.get_form_kwargs(),
            user=self.request.user,
            temp=True,
            token=self.kwargs["token"],
            is_invite=True,
            name=self.request.user.first_name + " " + self.request.user.last_name
        )

    def get_title_page(self):
        return self.get_object().survey.name

    def get_sub_title_page(self):
        return self.get_object().survey.description

    def get_context_data(self, *args, **kwargs):
        context = super(InviteEditSurveyFormView, self).get_context_data(*args, **kwargs)
        self.object.survey.last_activity = timezone.now()
        self.object.survey.save()
        context["edit_survey"] = self.object.survey
        context["organization"] = get_user_org(self.request.user)
        context["survey_question"] = VendorSurveyQuestion.objects.filter(survey=self.get_object().survey, is_deleted=False).first()
        context["token"] = self.kwargs["token"]
        return context

    def get_success_url(self):
        action_name = self.request.POST.get("action")
        url = reverse("djf_surveys:invite_questionnarie_redirect", args=[self.kwargs["token"]])
        url = url + f"?action={action_name}"
        return url


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="account_login")
def invite_questionnarie_redirect(request, token):
    action_data = request.GET.get("action", "")
    token_object = SurveyToken.objects.filter(key=token, user=request.user)
    context = {"action_data": action_data}
    if token_object:
        answer_object = VendorSurveyUserAnswer.objects.filter(survey=token_object.first().survey)
        if answer_object:
            url = reverse("djf_surveys:invite-survey-edit", args=[token_object.first().key, answer_object.first().id])
        else:
            url = reverse(
                "djf_surveys:invite-survey-create", args=[token_object.first().key, token_object.first().survey.slug]
            )
        context["redirect_url"] = url
        context["organization"] = get_user_org(token_object.first().user)
        context["token"] = token
        return render(request, "djf_surveys/email_redirect_questionnarie.html", context)
    context["token"] = False
    return render(request, "registration/survey_login.html", context)


def create_admin_headers(question_id, header):
    header_obj = QuestionHeader.objects.create(name=header)
    question_obj = OrgQuestion.objects.get(id=question_id)
    same_header_question = OrgQuestion.objects.filter(
        header=question_obj.header, ordering__gte=question_obj.ordering)
    question_obj.header = header_obj
    question_obj.save()
    same_header_question.update(header=header_obj)


def create_gracen_headers(question_id, header):
    header_obj = QuestionHeader.objects.create(name=header)
    question_obj = Question.objects.filter(id=question_id).first()
    same_header_question = Question.objects.filter(
        header=question_obj.header, ordering__gte=question_obj.ordering)
    question_obj.header = header_obj
    question_obj.save()
    same_header_question.update(header=header_obj)


def create_vendor_headers(question_id, header):
    header_obj = QuestionHeader.objects.create(name=header)
    question_obj = VendorSurveyQuestion.objects.filter(id=question_id).first()
    same_header_question = Question.objects.filter(
        header=question_obj.header, ordering__gte=question_obj.ordering)
    same_header_question.update(header=header_obj)
    question_obj.header = header_obj
    question_obj.save()


def remove_admin_header(question_id):
    question_obj = OrgQuestion.objects.filter(id=question_id).first()
    prev_question = OrgQuestion.objects.filter(ordering=question_obj.ordering-1,
                                               survey=question_obj.survey)
    all_remove_header = OrgQuestion.objects.filter(header=question_obj.header,
                                                   survey=question_obj.survey)
    if prev_question:
        all_remove_header.update(header=prev_question.first().header)
    ques_header = QuestionHeader.objects.filter(id=question_obj.header.id)
    if ques_header:
        ques_header.delete()


def remove_grc_header(question_id):
    question_obj = Question.objects.filter(id=question_id).first()
    prev_question = Question.objects.filter(ordering=question_obj.ordering-1,
                                               survey=question_obj.survey)
    all_remove_header = Question.objects.filter(header=question_obj.header,
                                                survey=question_obj.survey)
    if prev_question:
        all_remove_header.update(header=prev_question.first().header)
    ques_header = QuestionHeader.objects.filter(id=question_obj.header.id)
    if ques_header:
        ques_header.delete()


def remove_vendor_header(question_id):
    question_obj = VendorSurveyQuestion.objects.filter(id=question_id).first()
    prev_question = VendorSurveyQuestion.objects.filter(ordering=question_obj.ordering-1,
                                                        survey=question_obj.survey)
    all_remove_header = VendorSurveyQuestion.objects.filter(header=question_obj.header,
                                                            survey=question_obj.survey)
    if prev_question:
        all_remove_header.update(header=prev_question.first().header)
    ques_header = QuestionHeader.objects.filter(id=question_obj.header.id)
    if ques_header:
        ques_header.delete()


@login_required(login_url="account_login")
def create_question_header(request, question_id, survey_type=None):
    survey_type = request.GET.get("question_type")
    if request.method == "POST":
        if survey_type == "ADMIN":
            create_admin_headers(question_id, request.POST["header"])
        elif survey_type == "GRACEN_ADMIN":
            create_gracen_headers(question_id, request.POST["header"])
        elif survey_type == "VENDOR":
            create_vendor_headers(question_id, request.POST["header"])
    return HttpResponseRedirect(request.META.get("HTTP_REFERER"))


@login_required(login_url="account_login")
def remove_question_header(request, question_id, survey_type=None):
    survey_type = request.GET.get("question_type")
    if survey_type == "ADMIN":
        remove_admin_header(question_id)
    elif survey_type == "GRACEN_ADMIN":
        remove_grc_header(question_id)
    elif survey_type == "VENDOR":
        remove_vendor_header(question_id)
    return HttpResponseRedirect(request.META.get("HTTP_REFERER"))


@login_required(login_url="account_login")
def update_question_header(request, question_id, survey_type=None):
    survey_type = request.GET.get("question_type")
    if survey_type == "ADMIN":
        question_obj = OrgQuestion.objects.filter(id=question_id).first()
        QuestionHeader.objects.filter(name=question_obj.header).update(name=request.POST["header"])
    elif survey_type == "GRACEN_ADMIN":
        question_obj = Question.objects.filter(id=question_id).first()
        QuestionHeader.objects.filter(name=question_obj.header).update(name=request.POST["header"])
    elif survey_type == "VENDOR":
        question_obj = VendorSurveyQuestion.objects.filter(id=question_id).first()
        QuestionHeader.objects.filter(name=question_obj.header).update(name=request.POST["header"])
    return HttpResponseRedirect(request.META.get("HTTP_REFERER"))


def view_question_document(request, pk):
    answer = VendorSurveyAnswer.objects.filter(question__pk=pk).first()
    if not answer:
        return HttpResponseRedirect(request.META.get("HTTP_REFERER"))
    with default_storage.open(answer.document.name, "rb") as file:
        mime_type, _ = mimetypes.guess_type(answer.document.name)
        response = HttpResponse(file.read(), content_type=mime_type)
        response["Content-Disposition"] = f'inline; filename="{answer.question.label}"'
        return response
