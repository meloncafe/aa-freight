# Generated by Django 2.2.5 on 2019-11-08 22:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('freight', '0009_auto_20191030_2046'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contracthandler',
            name='operation_mode',
            field=models.CharField(default='my_alliance', help_text='defines what kind of contracts are synced', max_length=32),
        ),
    ]
