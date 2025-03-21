# Generated by Django 4.1.5 on 2023-03-14 04:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vendor", "0040_remove_historicalvendorsurveyuseranswer_user_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicalvendorsurveyquestion",
            name="help_text",
            field=models.CharField(
                blank=True,
                help_text="You can add a help text in here.",
                max_length=500,
                null=True,
                verbose_name="help text",
            ),
        ),
        migrations.AlterField(
            model_name="vendorsurveyquestion",
            name="help_text",
            field=models.CharField(
                blank=True,
                help_text="You can add a help text in here.",
                max_length=500,
                null=True,
                verbose_name="help text",
            ),
        ),
    ]
