# Generated by Django 4.1.5 on 2023-03-22 10:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vendor", "0043_survey_token_model"),
    ]

    operations = [
        migrations.AlterField(
            model_name="surveytoken",
            name="key",
            field=models.CharField(editable=False, max_length=255, unique=True),
        ),
    ]
