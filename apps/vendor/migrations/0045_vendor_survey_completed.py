# Generated by Django 4.1.5 on 2023-03-24 04:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vendor", "0044_alter_token_key"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalvendorsurvey",
            name="is_completed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="vendorsurvey",
            name="is_completed",
            field=models.BooleanField(default=False),
        ),
    ]
