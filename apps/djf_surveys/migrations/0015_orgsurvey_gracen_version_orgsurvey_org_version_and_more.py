# Generated by Django 4.1.5 on 2023-03-03 10:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djf_surveys", "0014_orgquestion_is_deleted_question_is_deleted"),
    ]

    operations = [
        migrations.AddField(
            model_name="orgsurvey",
            name="gracen_version",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="orgsurvey",
            name="org_version",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="survey",
            name="gracen_version",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="survey",
            name="org_version",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="orgquestion",
            name="type_field",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, "Text"),
                    (1, "Number"),
                    (2, "Radio"),
                    (3, "Select"),
                    (4, "Multi Select"),
                    (5, "Text Area"),
                    (6, "URL"),
                    (7, "Email"),
                    (8, "Date"),
                    (9, "Rating"),
                    (10, "Document"),
                ],
                verbose_name="type of input field",
            ),
        ),
        migrations.AlterField(
            model_name="question",
            name="type_field",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, "Text"),
                    (1, "Number"),
                    (2, "Radio"),
                    (3, "Select"),
                    (4, "Multi Select"),
                    (5, "Text Area"),
                    (6, "URL"),
                    (7, "Email"),
                    (8, "Date"),
                    (9, "Rating"),
                    (10, "Document"),
                ],
                verbose_name="type of input field",
            ),
        ),
    ]
