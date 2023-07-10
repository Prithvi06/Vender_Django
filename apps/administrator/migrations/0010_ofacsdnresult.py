# Generated by Django 3.2.6 on 2022-11-10 07:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0009_task_vendor'),
        ('vendor', '0019_alter_contact_role'),
        ('administrator', '0009_add_ALT_and_ADD_tables'),
    ]

    operations = [
        migrations.CreateModel(
            name='OFACSDNResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hash_code', models.CharField(max_length=255, unique=True)),
                ('total_sdn', models.PositiveBigIntegerField(default=0)),
                ('total_address', models.PositiveBigIntegerField(default=0)),
                ('total_alias', models.PositiveBigIntegerField(default=0)),
                ('result', models.JSONField(null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('task', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='tasks.task')),
                ('vendor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='vendor.vendor')),
            ],
        ),
    ]
