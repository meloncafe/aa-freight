# Generated by Django 2.2.5 on 2019-10-03 10:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jfservice', '0013_auto_20191003_1044'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='category',
            field=models.IntegerField(choices=[(3, 'station'), (65, 'structure'), (0, '(unknown)')], default=0),
        ),
    ]