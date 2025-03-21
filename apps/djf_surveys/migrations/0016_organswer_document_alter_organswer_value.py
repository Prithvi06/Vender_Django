# Generated by Django 4.1.5 on 2023-03-03 13:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djf_surveys", "0015_orgsurvey_gracen_version_orgsurvey_org_version_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="organswer",
            name="document",
            field=models.FileField(
                blank=True,
                help_text="The document of the answer given by the user.",
                max_length=4096,
                null=True,
                upload_to="",
                verbose_name="document",
            ),
        ),
        migrations.AlterField(
            model_name="organswer",
            name="value",
            field=models.TextField(
                blank=True,
                help_text="The value of the answer given by the user.",
                null=True,
                verbose_name="value",
            ),
        ),
    ]
