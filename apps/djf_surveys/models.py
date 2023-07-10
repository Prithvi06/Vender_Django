import random, string
from collections import namedtuple

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from organizations.models import Organization

from apps.djf_surveys import app_settings
from apps.djf_surveys.utils import create_star


TYPE_FIELD = namedtuple(
    "TYPE_FIELD", "text number radio select multi_select text_area url email date rating document yes_no_na"
)._make(range(12))


def generate_unique_slug(klass, field, id, identifier="slug"):
    """
    Generate unique slug.
    """
    origin_slug = slugify(field)
    unique_slug = origin_slug
    numb = 1
    mapping = {
        identifier: unique_slug,
    }
    obj = klass.objects.filter(**mapping).first()
    while obj:
        if obj.id == id:
            break
        rnd_string = random.choices(string.ascii_lowercase, k=(len(unique_slug)))
        unique_slug = "%s-%s-%d" % (origin_slug, "".join(rnd_string[:10]), numb)
        mapping[identifier] = unique_slug
        numb += 1
        obj = klass.objects.filter(**mapping).first()
    return unique_slug


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SurveyStatus(models.IntegerChoices):
    """known Question types"""

    NOT_SENT = 1
    SENT = 2
    VIEWED = 3
    IN_PROGRESS = 4
    IN_REVIEW = 5
    IN_REMEDIATION = 6
    COMPLETED = 7
    CANCELLED = 8


class BaseSurveyModel(models.Model):
    name = models.CharField(_("name"), max_length=200)
    description = models.TextField(_("description"), default="")
    slug = models.SlugField(_("slug"), max_length=225, default="")
    created_at = models.DateField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateField(null=True, blank=True, auto_now=True)
    active = models.BooleanField(default=True)
    gracen_version = models.FloatField(null=True, blank=True)
    org_version = models.FloatField(null=True, blank=True)
    status = models.IntegerField(choices=SurveyStatus.choices, null=True, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


def get_type_field_display(value):
    if value == 0:
        value = "Text"
    elif value == 1:
        value = "Number"
    elif value == 2:
        value = "Radio"
    elif value == 3:
        value = "Select"
    elif value == 4:
        value = "Multi Select"
    elif value == 5:
        value = "Text Area"
    elif value == 6:
        value = "URL"
    elif value == 7:
        value = "Email"
    elif value == 8:
        value = "Date"
    elif value == 9:
        value = "Rating"
    elif value == 10:
        value = "Document"
    elif value == 11:
        value = "Yes-No-NA"
    return value


class QuestionHeader(models.Model):
    name = models.CharField(max_length=1024, null=True, blank=True)

    def __str__(self):
        return self.name


class BaseQuestionModel(models.Model):
    TYPE_FIELD = [
        (TYPE_FIELD.text, _("Text")),
        (TYPE_FIELD.number, _("Number")),
        (TYPE_FIELD.radio, _("Radio")),
        (TYPE_FIELD.select, _("Select")),
        (TYPE_FIELD.multi_select, _("Multi Select")),
        (TYPE_FIELD.text_area, _("Text Area")),
        (TYPE_FIELD.url, _("URL")),
        (TYPE_FIELD.email, _("Email")),
        (TYPE_FIELD.date, _("Date")),
        (TYPE_FIELD.rating, _("Rating")),
        (TYPE_FIELD.document, _("Document")),
        (TYPE_FIELD.yes_no_na, _("Yes-No-NA")),
    ]

    key = models.CharField(
        _("key"),
        max_length=225,
        unique=True,
        default="",
        blank=True,
        help_text=_("Unique key for this question, fill in the blank if you want to use for automatic generation."),
    )
    label = models.CharField(_("label"), max_length=500, help_text=_("Enter your question in here."))
    type_field = models.PositiveSmallIntegerField(_("type of input field"), choices=TYPE_FIELD)
    choices = models.TextField(
        _("choices"),
        blank=True,
        null=True,
        help_text=_(
            "If type of field is radio, select, or multi select, fill in the options separated by commas. Ex: Male, Female."
        ),
    )
    help_text = models.CharField(
        _("help text"), max_length=500, blank=True, null=True, help_text=_("You can add a help text in here.")
    )
    required = models.BooleanField(
        _("required"), default=True, help_text=_("If True, the user must provide an answer to this question.")
    )
    ordering = models.PositiveIntegerField(
        _("ordering"), default=0, help_text=_("Defines the question order within the surveys.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    header = models.ForeignKey(QuestionHeader, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        abstract = True


class Survey(BaseSurveyModel):
    class Meta:
        verbose_name = _("survey")
        verbose_name_plural = _("surveys")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.slug:
            self.slug = generate_unique_slug(Survey, self.slug, self.id)
        else:
            self.slug = generate_unique_slug(Survey, self.name, self.id)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("survey")
        verbose_name_plural = _("surveys")


class OrgSurvey(BaseSurveyModel):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(get_user_model(), null=True, blank=True, on_delete=models.CASCADE)
    gracen_survey = models.ForeignKey(
        Survey,
        related_name="gracen_survey",
        on_delete=models.SET_NULL,
        verbose_name=_("survey"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("org_survey")
        verbose_name_plural = _("org_surveys")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.slug:
            self.slug = generate_unique_slug(OrgSurvey, self.slug, self.id)
        else:
            self.slug = generate_unique_slug(OrgSurvey, self.name, self.id)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("org_survey")
        verbose_name_plural = _("org_surveys")


class Question(BaseQuestionModel):
    survey = models.ForeignKey(Survey, related_name="questions", on_delete=models.CASCADE, verbose_name=_("survey"))

    class Meta:
        verbose_name = _("question")
        verbose_name_plural = _("questions")
        ordering = ["ordering"]

    def __str__(self):
        return f"{self.label}-survey-{self.survey.id}"

    def save(self, *args, **kwargs):
        if self.key:
            self.key = generate_unique_slug(Question, self.key, self.id, "key")
        else:
            self.key = generate_unique_slug(Question, self.label, self.id, "key")

        super(Question, self).save(*args, **kwargs)


class OrgQuestion(BaseQuestionModel):
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    survey = models.ForeignKey(OrgSurvey, related_name="questions", on_delete=models.CASCADE, verbose_name=_("survey"))

    class Meta:
        verbose_name = _("org_question")
        verbose_name_plural = _("org_questions")
        ordering = ["ordering"]

    def __str__(self):
        return f"{self.label}-survey-{self.survey.id}"

    def save(self, *args, **kwargs):
        if self.key:
            self.key = generate_unique_slug(OrgQuestion, self.key, self.id, "key")
        else:
            self.key = generate_unique_slug(OrgQuestion, self.label, self.id, "key")

        super(OrgQuestion, self).save(*args, **kwargs)


class UserAnswer(BaseModel):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, verbose_name=_("survey"))
    user = models.ForeignKey(get_user_model(), blank=True, null=True, on_delete=models.CASCADE, verbose_name=_("user"))

    class Meta:
        verbose_name = _("user answer")
        verbose_name_plural = _("user answers")
        ordering = ["-updated_at"]

    def __str__(self):
        return str(self.id)


class Answer(BaseModel):
    question = models.ForeignKey(
        Question, related_name="answers", on_delete=models.CASCADE, verbose_name=_("question")
    )
    value = models.TextField(_("value"), help_text=_("The value of the answer given by the user."))
    user_answer = models.ForeignKey(UserAnswer, on_delete=models.CASCADE, verbose_name=_("user answer"))
    na_explain = models.TextField(
        _("na_explain"),
        help_text=_("NA explain of the answer given by the user."),
        null=True,
        blank=True,
        max_length=500,
    )

    class Meta:
        verbose_name = _("answer")
        verbose_name_plural = _("answers")
        ordering = ["question__ordering"]

    def __str__(self):
        return f"{self.question}: {self.value}"

    @property
    def get_value(self):
        if self.question.type_field == TYPE_FIELD.rating:
            return create_star(active_star=int(self.value))
        elif self.question.type_field == TYPE_FIELD.url:
            return mark_safe(f'<a href="{self.value}" target="_blank">{self.value}</a>')
        elif (
            self.question.type_field == TYPE_FIELD.radio
            or self.question.type_field == TYPE_FIELD.select
            or self.question.type_field == TYPE_FIELD.multi_select
        ):
            return self.value.strip().replace("_", " ").capitalize()
        else:
            return self.value


class OrgUserAnswer(BaseModel):
    survey = models.ForeignKey(OrgSurvey, on_delete=models.CASCADE, verbose_name=_("survey"))
    user = models.ForeignKey(get_user_model(), blank=True, null=True, on_delete=models.CASCADE, verbose_name=_("user"))

    class Meta:
        verbose_name = _("user answer")
        verbose_name_plural = _("user answers")
        ordering = ["-updated_at"]

    def __str__(self):
        return str(self.id)


class OrgAnswer(BaseModel):
    question = models.ForeignKey(
        OrgQuestion, related_name="answers", on_delete=models.CASCADE, verbose_name=_("question")
    )
    value = models.TextField(
        _("value"), help_text=_("The value of the answer given by the user."), null=True, blank=True
    )
    document = models.FileField(
        _("document"),
        help_text=_("The document of the answer given by the user."),
        max_length=4096,
        null=True,
        blank=True,
    )
    user_answer = models.ForeignKey(OrgUserAnswer, on_delete=models.CASCADE, verbose_name=_("user answer"))
    na_explain = models.TextField(
        _("na_explain"),
        help_text=_("NA explain of the answer given by the user."),
        null=True,
        blank=True,
        max_length=500,
    )

    class Meta:
        verbose_name = _("answer")
        verbose_name_plural = _("answers")
        ordering = ["question__ordering"]

    def __str__(self):
        return f"{self.question}: {self.value}"

    @property
    def get_value(self):
        if self.question.type_field == TYPE_FIELD.rating:
            return create_star(active_star=int(self.value))
        elif self.question.type_field == TYPE_FIELD.url:
            return mark_safe(f'<a href="{self.value}" target="_blank">{self.value}</a>')
        elif (
            self.question.type_field == TYPE_FIELD.radio
            or self.question.type_field == TYPE_FIELD.select
            or self.question.type_field == TYPE_FIELD.multi_select
        ):
            return self.value.strip().replace("_", " ").capitalize()
        else:
            return self.value
