# Generated by Django 3.2.6 on 2022-11-29 11:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_user_last_visit'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='document_permission',
            field=models.PositiveIntegerField(blank=True, choices=[(0, 'View None'), (1, 'View Owned'), (2, 'View All'), (3, 'Edit Owned'), (4, 'Edit All')], null=True),
        ),
    ]
