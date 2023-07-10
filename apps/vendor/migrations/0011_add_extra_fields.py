# Generated by Django 3.2.6 on 2022-09-16 09:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vendor', '0010_add_additional_vendor_info'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='vendor.vendor'),
        ),
        migrations.AlterField(
            model_name='document',
            name='contract',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='vendor.contract'),
        ),
        migrations.AddField(
            model_name='document',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='document',
            name='updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
