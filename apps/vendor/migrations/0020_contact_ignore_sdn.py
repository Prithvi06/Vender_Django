# Generated by Django 3.2.6 on 2022-11-11 11:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0019_alter_contact_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='ignore_sdn',
            field=models.BooleanField(default=False),
        ),
    ]
