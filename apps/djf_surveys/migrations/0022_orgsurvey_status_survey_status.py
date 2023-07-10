# Generated by Django 4.1.5 on 2023-04-10 10:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djf_surveys", "0021_orgquestion_header_question_header"),
    ]

    operations = [
        migrations.AddField(
            model_name="orgsurvey",
            name="status",
            field=models.IntegerField(
                blank=True,
                choices=[
                    (1, "Not Sent"),
                    (2, "Sent"),
                    (3, "Viewed"),
                    (4, "In Progress"),
                    (5, "In Review"),
                    (6, "In Remediation"),
                    (7, "Complete"),
                    (8, "Cancelled"),
                ],
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="survey",
            name="status",
            field=models.IntegerField(
                blank=True,
                choices=[
                    (1, "Not Sent"),
                    (2, "Sent"),
                    (3, "Viewed"),
                    (4, "In Progress"),
                    (5, "In Review"),
                    (6, "In Remediation"),
                    (7, "Complete"),
                    (8, "Cancelled"),
                ],
                null=True,
            ),
        ),
    ]
