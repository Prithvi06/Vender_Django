# Generated by Django 4.1.5 on 2023-03-03 11:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vendor", "0037_contract_contract_optional_id_contract_created_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalvendorsurvey",
            name="gracen_version",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="historicalvendorsurvey",
            name="org_version",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="vendorsurvey",
            name="gracen_version",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="vendorsurvey",
            name="org_version",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="historicalvendorsurveyquestion",
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
            model_name="vendorsurveyquestion",
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
