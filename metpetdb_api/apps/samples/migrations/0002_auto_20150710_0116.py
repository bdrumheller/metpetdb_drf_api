# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('samples', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='subsample',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='samplemineral',
            name='mineral',
            field=models.ForeignKey(to='samples.Mineral'),
        ),
        migrations.AddField(
            model_name='samplemineral',
            name='sample',
            field=models.ForeignKey(to='samples.Sample'),
        ),
        migrations.AddField(
            model_name='sample',
            name='collector_id',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, blank=True, db_column='collector_id', related_name='+', null=True),
        ),
        migrations.AddField(
            model_name='sample',
            name='metamorphic_grades',
            field=models.ManyToManyField(to='samples.MetamorphicGrade'),
        ),
        migrations.AddField(
            model_name='sample',
            name='metamorphic_regions',
            field=models.ManyToManyField(to='samples.MetamorphicRegion'),
        ),
        migrations.AddField(
            model_name='sample',
            name='minerals',
            field=models.ManyToManyField(through='samples.SampleMineral', to='samples.Mineral'),
        ),
        migrations.AddField(
            model_name='sample',
            name='rock_type',
            field=models.ForeignKey(to='samples.RockType'),
        ),
        migrations.AddField(
            model_name='sample',
            name='user',
            field=models.ForeignKey(related_name='samples', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='mineral',
            name='real_mineral',
            field=models.ForeignKey(blank=True, to='samples.Mineral', null=True),
        ),
        migrations.AddField(
            model_name='grid',
            name='subsample',
            field=models.ForeignKey(to='samples.Subsample'),
        ),
    ]
