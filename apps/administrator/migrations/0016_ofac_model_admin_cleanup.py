# Generated by Django 3.2.16 on 2022-11-20 01:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('administrator', '0015_ofac_table_refactor'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ofacspeciallydesignatednational',
            options={'verbose_name': 'OFAC SDN', 'verbose_name_plural': 'OFAC SDNs'},
        ),
        migrations.AlterModelOptions(
            name='ofacspeciallydesignatednationaladdress',
            options={'verbose_name': 'OFAC Address', 'verbose_name_plural': 'OFAC Addresses'},
        ),
        migrations.AlterModelOptions(
            name='ofacspeciallydesignatednationalalternate',
            options={'verbose_name': 'OFAC Alias', 'verbose_name_plural': 'OFAC Aliases'},
        ),
    ]
