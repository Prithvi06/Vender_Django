from typing import List, Tuple

from django import forms
from django.db import transaction
from django.core.validators import MaxLengthValidator
from django.forms.widgets import DateInput
from apps.djf_surveys.models import (
    Answer,
    TYPE_FIELD,
    UserAnswer,
    Question,
    OrgAnswer,
    OrgUserAnswer,
    OrgQuestion,
    QuestionHeader,
    SurveyStatus,
)
from apps.djf_surveys.widgets import CheckboxSelectMultipleSurvey, RadioSelectSurvey, DateSurvey, RatingSurvey
from apps.djf_surveys.app_settings import DATE_INPUT_FORMAT, SURVEY_FIELD_VALIDATORS
from apps.djf_surveys.validators import validate_rating
import os
from uuid import uuid4
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from apps.vendor.models import SurveyToken, VendorSurvey
from datetime import datetime


def make_choices(question: Question) -> List[Tuple[str, str]]:
    choices = []
    for choice in question.choices.split(","):
        choice = choice.strip()
        choices.append((choice.replace(" ", "_").lower(), choice))
    return choices


class BaseSurveyForm(forms.Form):
    def __init__(self, survey, user, *args, **kwargs):
        self.survey = survey
        self.is_invite = kwargs.pop("is_invite", False)
        self.user = user if user.is_authenticated else None
        if self.is_invite:
            self.user = None
        self.field_names = []
        self.questions = self.survey.questions.exclude(is_deleted=True).order_by("ordering")
        self.temp = kwargs.pop("temp", None)
        self.token = kwargs.pop("token", None)
        self.name = kwargs.pop("name", False)

        super().__init__(*args, **kwargs)

        for index, question in enumerate(self.questions):
            # to generate field name
            field_name = f"field_survey_{question.id}"
            is_required = question.required
            if hasattr(question, "vendor") and not self.temp:
                is_required = False
            
            if question.type_field == TYPE_FIELD.multi_select:
                choices = make_choices(question)
                self.fields[field_name] = forms.MultipleChoiceField(
                    choices=choices,
                    label=question.label,
                    widget=CheckboxSelectMultipleSurvey,
                    required=is_required,
                )
                self.fields[field_name].widget.attrs["value"] = question.answers.first().value if question.answers.first() else ''
                self.fields[field_name].widget.attrs["required"] = is_required
            elif question.type_field == TYPE_FIELD.radio:
                choices = make_choices(question)
                self.fields[field_name] = forms.ChoiceField(
                    choices=choices, label=question.label, widget=RadioSelectSurvey,
                    required=is_required,
                )
            elif question.type_field == TYPE_FIELD.yes_no_na:
                choices = make_choices(question)
                self.fields[field_name] = forms.ChoiceField(
                    choices=choices, label=question.label, widget=RadioSelectSurvey,
                    required=is_required,
                )
                if question.answers.first():
                    self.fields[field_name].widget.attrs["na_explain_value"] = (
                        question.answers.first().na_explain if question.answers.first().na_explain else ""
                    )
                else:
                    self.fields[field_name].widget.attrs["na_explain_value"] = ""
                self.fields[field_name].widget.attrs["question_type"] = "Yes-No-NA"
                self.fields["na_explain_" + str(question.id)] = forms.CharField(
                    label=question.label, widget=forms.Textarea, required=False
                )
                self.fields["na_explain_" + str(question.id)].widget.attrs["question_type"] = "na_explain"
            elif question.type_field == TYPE_FIELD.select:
                choices = [("", "-------")]
                choices.extend(make_choices(question))
                self.fields[field_name] = forms.ChoiceField(
                    choices=choices, label=question.label,
                    required=is_required
                )
            elif question.type_field == TYPE_FIELD.number:
                self.fields[field_name] = forms.IntegerField(
                    label=question.label,
                    required=is_required
                )
            elif question.type_field == TYPE_FIELD.url:
                self.fields[field_name] = forms.URLField(
                    label=question.label, validators=[MaxLengthValidator(SURVEY_FIELD_VALIDATORS["max_length"]["url"])],
                    required=is_required,
                )
                self.fields[field_name].widget.attrs['placeholder'] = "https://example.com"
                self.fields[field_name].widget.attrs['pattern'] = "^((http|https)://)[-a-zA-Z0-9@:%._\\+~#?&//=]{2,256}\\.[a-z]{2,6}\\b([-a-zA-Z0-9@:%._\\+~#?&//=]*)$"
            elif question.type_field == TYPE_FIELD.email:
                self.fields[field_name] = forms.EmailField(
                    label=question.label,
                    validators=[MaxLengthValidator(SURVEY_FIELD_VALIDATORS["max_length"]["email"])],
                    required=is_required,
                )
                self.fields[field_name].widget.attrs['title'] = "Valid e-mail address including top-level domain"
                self.fields[field_name].widget.attrs['pattern'] = "^([\w\.\-]+)@([\w\-]+)((\.(\w){2,3})+)$"
            elif question.type_field == TYPE_FIELD.date:
                self.fields[field_name] = forms.DateField(
                    label=question.label, required=is_required,
                )
                self.fields[field_name].widget.attrs = {"indicator": "date"}
            elif question.type_field == TYPE_FIELD.text_area:
                self.fields[field_name] = forms.CharField(
                    label=question.label, widget=forms.Textarea,
                    required=is_required,
                )
                self.fields[field_name].widget.attrs = {"style": "border: 1px solid #2f4f4f6b; min-height: 115px; border-bottom: none"}
            elif question.type_field == TYPE_FIELD.rating:
                self.fields[field_name] = forms.CharField(
                    label=question.label, widget=RatingSurvey,
                    validators=[MaxLengthValidator(1), validate_rating],
                    required=is_required,
                )
            elif question.type_field == TYPE_FIELD.document:
                self.fields[field_name] = forms.FileField(label=question.label, required=is_required)
            else:
                self.fields[field_name] = forms.CharField(
                    label=question.label,
                    validators=[MaxLengthValidator(SURVEY_FIELD_VALIDATORS["max_length"]["text"])],
                    required=is_required,
                )
                self.fields[field_name].widget.attrs = {"onkeyup":"charCount(this)"}
            
            if hasattr(question, "vendor") and not self.temp:
                self.fields[field_name].required = False
                self.fields[field_name].user = ""
            # self.fields[field_name].widget.attrs["required"] = is_required
            self.fields[field_name].widget.attrs["question_key"] = question.key
            self.fields[field_name].widget.attrs["question_id"] = question.id
            self.fields[field_name].widget.attrs["question_count"] = index + 1
            header = self.questions.filter(header=question.header).order_by("ordering").first()
            if header == question:
                self.fields[field_name].widget.attrs["header"] = question.header
                self.fields[field_name].widget.attrs["header_question_count"] = self.questions.filter(header=question.header).count()
            self.fields[field_name].help_text = question.help_text
            self.field_names.append(field_name)
        if self.temp:
            self.fields["action"] = forms.CharField()
            self.fields["action"].widget.attrs = {"style": "display: none;", "id": "action_val"}

    def clean(self):
        try:
            action = self.cleaned_data["action"]
            # changing status of survey
            if self.is_invite:
                if action == "CONTINUE":
                    if self.survey.status != SurveyStatus.IN_REVIEW:
                        self.survey.status = SurveyStatus.IN_PROGRESS
                        self.survey.save()
                elif action == "SAVE":
                    self.survey.status = SurveyStatus.IN_REVIEW
                    self.survey.save()
            if action == "CONTINUE":
                self.empty_permitted = True
                self._errors = {}
                for field_name in self.field_names:
                    try:
                        field = self.cleaned_data[field_name]
                    except KeyError:
                        self.cleaned_data[field_name] = ""
                return self.cleaned_data
            else:
                cleaned_data = super().clean()
                for field_name in self.field_names:
                    try:
                        field = cleaned_data[field_name]
                    except KeyError:
                        raise forms.ValidationError("You must enter valid data")
                if self.fields[field_name].required and not field:
                    self.add_error(field_name, "This field is required")
                token_object = SurveyToken.objects.filter(key=self.token)
                if token_object:
                    VendorSurvey.objects.filter(id=token_object.first().survey.pk).update(is_completed=True)
                return cleaned_data
        except Exception as e:
            cleaned_data = super().clean()
            for field_name in self.field_names:
                try:
                    field = cleaned_data[field_name]
                except KeyError:
                    raise forms.ValidationError("You must enter valid data")
            if self.fields[field_name].required and not field:
                self.add_error(field_name, "This field is required")
            return cleaned_data


class CreateSurveyForm(BaseSurveyForm):
    @transaction.atomic
    def save(self):
        from apps.vendor.models import VendorSurveyUserAnswer, VendorSurveyAnswer

        cleaned_data = super().clean()
        user_answer = VendorSurveyUserAnswer.objects.filter(survey=self.survey, vendor=self.survey.vendor)
        if not user_answer.exists():
            user_answer = VendorSurveyUserAnswer.objects.create(survey=self.survey, vendor=self.survey.vendor)
        else:
            user_answer = user_answer.first()
        for question in self.questions:
            document = None
            field_name = f"field_survey_{question.id}"

            if question.type_field == TYPE_FIELD.multi_select:
                value = ",".join(cleaned_data[field_name])
                if len(value) == 0:
                    value = ""
            elif question.type_field == TYPE_FIELD.document:
                document = cleaned_data[field_name]
                value = ""
            elif question.type_field == TYPE_FIELD.number:
                value = cleaned_data[field_name]
                if value == None:
                    value = ""
            else:
                value = cleaned_data[field_name]
            vendor_ans = VendorSurveyAnswer.objects.filter(question=question, user_answer=user_answer)
            if not vendor_ans.exists():
                if question.type_field == TYPE_FIELD.document:
                    try:
                        if document:
                            file = document
                            filename, ext = os.path.splitext(os.path.basename(file.name))
                            filename = f"{filename}-{uuid4()}{ext}"
                            filepath = f"{question.vendor.org.id}/{question.vendor.id}/Questionnaire/{question.label}/{filename}"
                            file_data = file.read()
                            answer_object = VendorSurveyAnswer(
                                question=question,
                                document=default_storage.save(filepath, ContentFile(file_data)),
                                user_answer=user_answer,
                                user=self.user,
                            )
                            if self.is_invite:
                                answer_object.answer_by_invited_user = True
                            answer_object.save()
                    except Exception as e:
                        pass
                else:
                    answer_object = VendorSurveyAnswer(
                        question=question, user=self.user, value=value, user_answer=user_answer
                    )
                    if self.is_invite:
                        answer_object.answer_by_invited_user = True
                    if question.type_field == TYPE_FIELD.yes_no_na:
                        answer_object.na_explain = cleaned_data["na_explain_" + str(question.id)]
                    answer_object.save()
                    # if self.is_invite:
                    answer_object.history.filter(pk=answer_object.history.latest().pk).update(history_user=self.user, name=self.name)
            else:
                if question.type_field == TYPE_FIELD.document:
                    try:
                        if document:
                            file = document
                            filename, ext = os.path.splitext(os.path.basename(file.name))
                            filename = f"{filename}-{uuid4()}{ext}"
                            filepath = f"{question.vendor.org.id}/{question.vendor.id}/Questionnaire/{question.label}/{filename}"
                            file_data = file.read()
                            vendor_ans.update(
                                document=default_storage.save(filepath, ContentFile(file_data)), user=self.user
                            )
                            if self.is_invite:
                                vendor_ans.update(answer_by_invited_user=True)
                    except Exception as e:
                        pass
                else:
                    vendor_ans.update(value=value, user=self.user)
                    if question.type_field == TYPE_FIELD.yes_no_na:
                        vendor_ans.update(na_explain=cleaned_data["na_explain_" + str(question.id)])
                    if self.is_invite:
                        vendor_ans.update(answer_by_invited_user=True)
                    vendor_ans.first().history.filter(pk=vendor_ans.first().history.latest().pk).update(history_user=self.user, name=self.name)


class EditSurveyForm(BaseSurveyForm):
    def __init__(self, user_answer, *args, **kwargs):
        self.survey = user_answer.survey
        self.user_answer = user_answer
        self.user = kwargs.pop("user", None)
        super().__init__(survey=self.survey, user=self.user, *args, **kwargs)
        self._set_initial_data()

    def _set_initial_data(self):
        from apps.vendor.models import VendorSurveyAnswer

        answers = VendorSurveyAnswer.objects.filter(user_answer=self.user_answer).exclude(question__is_deleted=True)
        # if self.is_invite:
        #     answers = answers.filter(answer_by_invited_user=True)
        for answer in answers:
            field_name = f"field_survey_{answer.question.id}"
            if answer.user:
                self.fields[field_name].widget.attrs["user"] = answer.user.first_name + " " + answer.user.last_name
            if answer.question.type_field == TYPE_FIELD.multi_select:
                self.fields[field_name].initial = answer.value.split(",") if answer.value != '' else '' 
            elif answer.question.type_field == TYPE_FIELD.document:
                self.fields[field_name].initial = answer.document
            else:
                self.fields[field_name].initial = answer.value
                if answer.question.type_field == TYPE_FIELD.yes_no_na:
                    self.fields["na_explain_" + str(answer.question.id)].initial = answer.na_explain

    @transaction.atomic
    def save(self):
        from apps.vendor.models import VendorSurveyAnswer

        cleaned_data = super().clean()
        self.user_answer.survey = self.survey
        self.user_answer.user = self.user
        self.user_answer.save()
        for question in self.questions:
            field_name = f"field_survey_{question.id}"
            document = None
            if question.type_field == TYPE_FIELD.multi_select:
                value = ",".join(cleaned_data[field_name])
                if len(value) == 0:
                    value = ""
            elif question.type_field == TYPE_FIELD.document:
                document = cleaned_data[field_name]
            elif question.type_field == TYPE_FIELD.number:
                value = cleaned_data[field_name]
                if value == None:
                    value = ""
            else:
                value = cleaned_data[field_name]

            answer, created = VendorSurveyAnswer.objects.get_or_create(
                question=question,
                user_answer=self.user_answer,
                defaults={"question_id": question.id, "user_answer_id": self.user_answer.id},
            )
            if question.type_field == TYPE_FIELD.yes_no_na:
                answer.na_explain = cleaned_data["na_explain_" + str(question.id)]
                if value:
                    answer.value = value
                # answer.save()
            if not created and answer:
                if question.type_field == TYPE_FIELD.document:
                    try:
                        if answer.document != document:
                            file = document
                            filename, ext = os.path.splitext(os.path.basename(file.name))
                            filename = f"{filename}-{uuid4()}{ext}"
                            filepath = f"{question.vendor.org.id}/{question.vendor.id}/Questionnaire/{question.label}/{filename}"
                            file_data = file.read()
                            answer.document = default_storage.save(filepath, ContentFile(file_data))
                            answer.user = self.user
                            if self.is_invite:
                                answer.answer_by_invited_user = True
                    except Exception as e:
                        pass
                else:
                    prev_value = answer.value
                    if question.type_field == TYPE_FIELD.number and prev_value:
                        prev_value = int(prev_value)
                    if question.type_field == TYPE_FIELD.date and prev_value:
                        prev_value = datetime.strptime(prev_value, '%Y-%m-%d').date()

                    if value != prev_value:
                        answer.user = self.user
                        if self.is_invite:
                            answer.answer_by_invited_user = True
                    answer.value = value
            answer.save()
            answer.history.filter(pk=answer.history.latest().pk).update(history_user=self.user, name=self.name)


class AdminCreateSurveyForm(BaseSurveyForm):
    @transaction.atomic
    def save(self):
        cleaned_data = super().clean()
        user_answer = UserAnswer.objects.filter(survey=self.survey, user=self.user)
        if not user_answer.exists():
            user_answer = UserAnswer.objects.create(survey=self.survey, user=self.user)
        else:
            user_answer = user_answer.first()
        for question in self.questions:
            field_name = f"field_survey_{question.id}"

            if question.type_field == TYPE_FIELD.multi_select:
                value = ",".join(cleaned_data[field_name])
            else:
                value = cleaned_data[field_name]
            vendor_ans = Answer.objects.filter(question=question, user_answer=user_answer)
            if not vendor_ans.exists():
                Answer.objects.create(question=question, value=value, user_answer=user_answer)
            else:
                vendor_ans.update(value=value)


class AdminEditSurveyForm(BaseSurveyForm):
    def __init__(self, user_answer, *args, **kwargs):
        self.survey = user_answer.survey
        self.user_answer = user_answer
        super().__init__(survey=self.survey, user=user_answer.user, *args, **kwargs)
        self._set_initial_data()

    def _set_initial_data(self):

        answers = Answer.objects.filter(user_answer=self.user_answer)

        for answer in answers:
            field_name = f"field_survey_{answer.question.id}"
            if answer.question.type_field == TYPE_FIELD.multi_select:
                self.fields[field_name].initial = answer.value.split(",")
            else:
                self.fields[field_name].initial = answer.value

    @transaction.atomic
    def save(self):
        cleaned_data = super().clean()
        self.user_answer.survey = self.survey
        self.user_answer.user = self.user
        self.user_answer.save()

        for question in self.questions:
            field_name = f"field_survey_{question.id}"
            if question.type_field == TYPE_FIELD.multi_select:
                value = ",".join(cleaned_data[field_name])
            else:
                value = cleaned_data[field_name]

            answer, created = Answer.objects.get_or_create(
                question=question,
                user_answer=self.user_answer,
                defaults={"question_id": question.id, "user_answer_id": self.user_answer.id},
            )

            if not created and answer:
                answer.value = value
                answer.save()


class OrgAdminCreateSurveyForm(BaseSurveyForm):
    @transaction.atomic
    def save(self):
        cleaned_data = super().clean()
        user_answer = OrgUserAnswer.objects.filter(survey=self.survey, user=self.user)
        if not user_answer.exists():
            user_answer = OrgUserAnswer.objects.create(survey=self.survey, user=self.user)
        else:
            user_answer = user_answer.first()
        for question in self.questions:
            document = None
            field_name = f"field_survey_{question.id}"

            if question.type_field == TYPE_FIELD.multi_select:
                value = ",".join(cleaned_data[field_name])
            elif question.type_field == TYPE_FIELD.document:
                document = cleaned_data[field_name]
                value = None
            else:
                value = cleaned_data[field_name]
            vendor_ans = OrgAnswer.objects.filter(question=question, user_answer=user_answer)
            if not vendor_ans.exists():
                if value:
                    answer_object = OrgAnswer.objects.create(question=question, value=value, user_answer=user_answer)
                    if question.type_field == TYPE_FIELD.yes_no_na:
                        answer_object.na_explain = cleaned_data["na_explain_" + str(question.id)]
                        answer_object.save()
                elif question.type_field == TYPE_FIELD.document:
                    try:
                        if document:
                            file = document
                            filename, ext = os.path.splitext(os.path.basename(file.name))
                            filename = f"{filename}-{uuid4()}{ext}"

                            filepath = f"{question.org.id}/Questionnaire/{question.label}/{filename}"
                            file_data = file.read()
                            OrgAnswer.objects.create(
                                question=question,
                                document=default_storage.save(filepath, ContentFile(file_data)),
                                user_answer=user_answer,
                            )
                    except Exception as e:
                        pass
            else:
                if question.type_field == TYPE_FIELD.document:
                    try:
                        if document:
                            file = document
                            filename, ext = os.path.splitext(os.path.basename(file.name))
                            filename = f"{filename}-{uuid4()}{ext}"

                            filepath = f"{question.org.id}/Questionnaire/{question.label}/{filename}"
                            file_data = file.read()
                            vendor_ans.update(document=default_storage.save(filepath, ContentFile(file_data)))
                    except Exception as e:
                        pass
                else:
                    vendor_ans.update(value=value)
                    if question.type_field == TYPE_FIELD.yes_no_na:
                        vendor_ans.update(na_explain=cleaned_data["na_explain_" + str(question.id)])


class OrgAdminEditSurveyForm(BaseSurveyForm):
    def __init__(self, user_answer, *args, **kwargs):
        self.survey = user_answer.survey
        self.user_answer = user_answer
        super().__init__(survey=self.survey, user=user_answer.user, *args, **kwargs)
        self._set_initial_data()

    def _set_initial_data(self):

        answers = OrgAnswer.objects.filter(user_answer=self.user_answer).exclude(question__is_deleted=True)

        for answer in answers:
            field_name = f"field_survey_{answer.question.id}"
            if answer.question.type_field == TYPE_FIELD.multi_select:
                if answer.value:
                    self.fields[field_name].initial = answer.value.split(",")
            elif answer.question.type_field == TYPE_FIELD.document:
                self.fields[field_name].initial = answer.document
            else:
                self.fields[field_name].initial = answer.value
                if answer.question.type_field == TYPE_FIELD.yes_no_na:
                    self.fields["na_explain_" + str(answer.question.id)].initial = answer.na_explain

    @transaction.atomic
    def save(self):
        cleaned_data = super().clean()
        self.user_answer.survey = self.survey
        self.user_answer.user = self.user
        self.user_answer.save()
        for question in self.questions:
            document = None
            field_name = f"field_survey_{question.id}"

            if question.type_field == TYPE_FIELD.multi_select:
                value = ",".join(cleaned_data[field_name])
            elif question.type_field == TYPE_FIELD.document:
                document = cleaned_data[field_name]
                value = ""
            else:
                value = cleaned_data[field_name]

            answer, created = OrgAnswer.objects.get_or_create(
                question=question,
                user_answer=self.user_answer,
                defaults={"question_id": question.id, "user_answer_id": self.user_answer.id},
            )
            if question.type_field == TYPE_FIELD.yes_no_na:
                answer.na_explain = cleaned_data["na_explain_" + str(question.id)]
                if value:
                    answer.value = value
                answer.save()

            if not created and answer and (value or document):
                if question.type_field == TYPE_FIELD.document:
                    try:
                        if document:
                            file = document
                            filename, ext = os.path.splitext(os.path.basename(file.name))
                            filename = f"{filename}-{uuid4()}{ext}"

                            filepath = f"{question.org.id}/Questionnaire/{question.label}/{filename}"
                            file_data = file.read()
                            answer.document = default_storage.save(filepath, ContentFile(file_data))
                    except Exception as e:
                        pass
                else:
                    answer.value = value
                answer.save()
