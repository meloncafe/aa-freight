# Generated by Django 2.2.5 on 2019-10-04 11:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jfservice', '0001_squashed_0015_auto_20191003_1305'),
    ]

    operations = [
        migrations.RenameField(
            model_name='pricing',
            old_name='pricing_comment',
            new_name='comment',
        ),
    ]