# Generated by Django 4.1.5 on 2023-03-16 13:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("djf_surveys", "0018_alter_orgquestion_help_text_alter_question_help_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="orgsurvey",
            name="gracen_survey",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="gracen_survey",
                to="djf_surveys.survey",
                verbose_name="survey",
            ),
        ),
        migrations.AddField(
            model_name="orgsurvey",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
