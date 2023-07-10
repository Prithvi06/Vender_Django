# Generated by Django 3.2.6 on 2022-12-19 11:35

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vendor", "0027_merge_0026_historicaldocument_0026_historicalvendor"),
        ("notes", "0002_commentslog_task"),
    ]

    operations = [
        migrations.AddField(
            model_name="commentslog",
            name="contact",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="vendor.contact"
            ),
        ),
    ]
