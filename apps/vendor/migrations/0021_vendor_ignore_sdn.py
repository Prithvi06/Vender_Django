# Generated by Django 3.2.6 on 2022-11-15 07:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0020_contact_ignore_sdn'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendor',
            name='ignore_sdn',
            field=models.BooleanField(default=False),
        ),
    ]
