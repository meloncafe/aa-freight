# Generated by Django 2.2.5 on 2019-10-02 11:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('authentication', '0016_ownershiprecord'),
        ('eveonline', '0010_alliance_ticker'),
        ('evesde', '0014_delete_evename'),
    ]

    operations = [
        migrations.CreateModel(
            name='Structure',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('position_x', models.FloatField()),
                ('position_y', models.FloatField()),
                ('position_z', models.FloatField()),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='eveonline.EveCorporationInfo')),
                ('solar_system', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='evesde.EveSolarSystem')),
                ('type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='evesde.EveType')),
            ],
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.BigIntegerField(primary_key=True, serialize=False)),
                ('item', models.OneToOneField(default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, to='evesde.EveItem')),
                ('structure', models.OneToOneField(default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, to='jfservice.Structure')),
            ],
        ),
        migrations.CreateModel(
            name='JfService',
            fields=[
                ('alliance', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='eveonline.EveAllianceInfo')),
                ('price_per_volume', models.FloatField(default=None, null=True)),
                ('price_collateral_percent', models.FloatField(default=None, null=True)),
                ('collateral_max', models.BigIntegerField(default=None, null=True)),
                ('price_minimum', models.FloatField(default=None, null=True)),
                ('character', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_DEFAULT, to='authentication.CharacterOwnership')),
            ],
            options={
                'permissions': (('access_jfservice', 'Can access the JF Service'),),
            },
        ),
        migrations.CreateModel(
            name='Contract',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('collateral', models.FloatField()),
                ('contract_id', models.IntegerField()),
                ('date_accepted', models.DateTimeField(default=None, null=True)),
                ('date_completed', models.DateTimeField(default=None, null=True)),
                ('date_expired', models.DateTimeField()),
                ('date_issued', models.DateTimeField()),
                ('days_to_complete', models.IntegerField()),
                ('for_corporation', models.BooleanField()),
                ('price', models.FloatField()),
                ('reward', models.FloatField()),
                ('status', models.CharField(max_length=32)),
                ('title', models.CharField(default=None, max_length=100, null=True)),
                ('volume', models.FloatField()),
                ('acceptor', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='contract_acceptor', to='eveonline.EveCharacter')),
                ('end_location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contract_end_location', to='jfservice.Location')),
                ('issue_corporation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contract_issuer', to='eveonline.EveCorporationInfo')),
                ('issuer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contract_issuer', to='eveonline.EveCharacter')),
                ('jfservice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='jfservice.JfService')),
                ('start_location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contract_start_location', to='jfservice.Location')),
            ],
        ),
        migrations.AddIndex(
            model_name='contract',
            index=models.Index(fields=['status'], name='jfservice_c_status_67ae0d_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='contract',
            unique_together={('jfservice', 'contract_id')},
        ),
    ]