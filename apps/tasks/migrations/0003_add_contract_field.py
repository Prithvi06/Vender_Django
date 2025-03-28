# Generated by Django 3.2.6 on 2022-10-06 06:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0017_add_phone_is_delete'),
        ('tasks', '0002_task_contact'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='contract',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='vendor.contract'),
        ),
        migrations.AddField(
            model_name='task',
            name='renewal_reminder_date',
            field=models.DateField(blank=True, editable=False, null=True),
        ),
    ]
