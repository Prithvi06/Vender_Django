# Generated by Django 3.2.6 on 2022-07-07 00:07

import django.db.models.deletion
import django.db.models.expressions
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vendor", "0008_alter_vendor_owner"),
    ]

    operations = [
        migrations.AddField(
            model_name="contract",
            name="parent_contract",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="child_contracts",
                to="vendor.contract",
            ),
        ),
        migrations.AddField(
            model_name="historicalcontract",
            name="parent_contract",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="vendor.contract",
            ),
        ),
        migrations.AddConstraint(
            model_name="contract",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("parent_contract__isnull", True),
                    models.Q(("parent_contract_id", django.db.models.expressions.F("id")), _negated=True),
                    _connector="OR",
                ),
                name="contract_cannot_reference_self",
            ),
        ),
    ]
