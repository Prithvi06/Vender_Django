# Generated by Django 4.1.5 on 2023-04-11 08:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vendor", "0048_add_survey_status"),
    ]

    operations = [
        # migrations.AlterField(
        #     model_name="historicalvendorsurvey",
        #     name="status",
        #     field=models.IntegerField(
        #         blank=True,
        #         choices=[
        #             (1, "Not Sent"),
        #             (2, "Sent"),
        #             (3, "Viewed"),
        #             (4, "In Progress"),
        #             (5, "In Review"),
        #             (6, "In Remediation"),
        #             (7, "Completed"),
        #             (8, "Cancelled"),
        #         ],
        #         null=True,
        #     ),
        # ),
        # migrations.AlterField(
        #     model_name="vendorsurvey",
        #     name="status",
        #     field=models.IntegerField(
        #         blank=True,
        #         choices=[
        #             (1, "Not Sent"),
        #             (2, "Sent"),
        #             (3, "Viewed"),
        #             (4, "In Progress"),
        #             (5, "In Review"),
        #             (6, "In Remediation"),
        #             (7, "Completed"),
        #             (8, "Cancelled"),
        #         ],
        #         null=True,
        #     ),
        # ),
    ]
