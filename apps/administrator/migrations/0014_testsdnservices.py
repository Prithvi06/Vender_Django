# Generated by Django 3.2.6 on 2022-11-14 06:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administrator', '0013_ofacsdnresult_contact'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestSDNServices',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_name', models.CharField(choices=[('DOWNLOAD_OFAC_FILES', 'DOWNLOAD_OFAC_FILES'), ('OFAC_SCAN_ON_CONTACT', 'OFAC_SCAN_ON_CONTACT')], max_length=100, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
