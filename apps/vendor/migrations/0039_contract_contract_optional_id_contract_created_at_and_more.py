# Generated by Django 4.1.5 on 2023-03-06 09:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("vendor", "0038_contract_contract_optional_id_contract_created_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalvendorsurveyanswer",
            name="document",
            field=models.TextField(
                blank=True,
                help_text="The document of the answer given by the user.",
                max_length=4096,
                null=True,
                verbose_name="document",
            ),
        ),
        migrations.AddField(
            model_name="vendorsurveyanswer",
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
            model_name="historicalvendorsurveyanswer",
            name="value",
            field=models.TextField(
                blank=True,
                help_text="The value of the answer given by the user.",
                null=True,
                verbose_name="value",
            ),
        ),
        migrations.AlterField(
            model_name="vendorsurveyanswer",
            name="value",
            field=models.TextField(
                blank=True,
                help_text="The value of the answer given by the user.",
                null=True,
                verbose_name="value",
            ),
        ),
    ]
