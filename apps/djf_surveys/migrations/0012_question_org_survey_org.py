# Generated by Django 4.1.5 on 2023-01-13 10:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        (
            "organizations",
            "0004_organizationinvitation",
        ),
        ("djf_surveys", "0011_survey_active_alter_survey_created_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="org",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="organizations.organization",
            ),
        ),
        migrations.AddField(
            model_name="survey",
            name="org",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="organizations.organization",
            ),
        ),
    ]
