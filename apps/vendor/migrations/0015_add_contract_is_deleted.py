# Generated by Django 3.2.6 on 2022-09-23 08:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0014_add_contact_is_deleted'),
    ]

    operations = [
        migrations.AddField(
            model_name='contract',
            name='is_deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='historicalcontract',
            name='is_deleted',
            field=models.BooleanField(default=False),
        )
    ]
