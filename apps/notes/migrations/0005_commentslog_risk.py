# Generated by Django 3.2.16 on 2023-01-01 00:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("risks", "0006_historicalrisk"),
        ("notes", "0004_merge_20221229_1250"),
    ]

    operations = [
        migrations.AddField(
            model_name="commentslog",
            name="risk",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="risks.risk"
            ),
        ),
    ]
