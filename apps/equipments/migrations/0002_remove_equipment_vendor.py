# Generated by Django 4.1.7 on 2023-05-05 15:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("equipments", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="equipment",
            name="vendor",
        ),
    ]
