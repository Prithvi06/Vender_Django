# Generated by Django 3.2.6 on 2022-06-12 06:11
# pylint: disable=missing-module-docstring
# pylint: disable=invalid-name
# pylint: disable=missing-class-docstring
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vendor", "0002_contract_is_auto_renew"),
    ]

    operations = [
        migrations.AddField(
            model_name="vendor",
            name="tax_id_number",
            field=models.CharField(
                blank=True,
                db_column="tax_id_number",
                max_length=9,
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        "^\\d{2}-\\d{7}$|^\\d{9}$",
                        "Expected format: 12-1234567.  The dash is optional.",
                    )
                ],
            ),
        ),
        migrations.AddConstraint(
            model_name="vendor",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("tax_id_number__isnull", True),
                    ("tax_id_number__length", 9),
                    _connector="OR",
                ),
                name="tax_id_number_min_length",
            ),
        ),
        migrations.AddConstraint(
            model_name="vendor",
            constraint=models.UniqueConstraint(
                condition=models.Q(("tax_id_number__isnull", False)),
                fields=("org", "tax_id_number"),
                name="tax_id_number_unique_within_org",
            ),
        ),
    ]
