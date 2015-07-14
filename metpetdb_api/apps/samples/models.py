import uuid
from concurrency.fields import AutoIncVersionField

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField


class RockType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(unique=True, max_length=100)

    class Meta:
        db_table = 'rock_types'


class Sample(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = AutoIncVersionField()
    public_data = models.BooleanField(default=False)
    number = models.CharField(max_length=35)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='samples')
    aliases = ArrayField(models.CharField(max_length=35, blank=True),
                         blank=True,
                         null=True)
    collection_date = models.DateTimeField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    location_name = models.CharField(max_length=50, blank=True, null=True)
    location_coords = models.PointField()
    location_error = models.FloatField(blank=True, null=True)
    rock_type = models.ForeignKey(RockType)
    date_precision = models.SmallIntegerField(blank=True, null=True)
    metamorphic_regions = models.ManyToManyField('MetamorphicRegion')
    metamorphic_grades = models.ManyToManyField('MetamorphicGrade')
    minerals = models.ManyToManyField('Mineral', through='SampleMineral',
                                      related_name='samples')

    # Free-text field. Ugh. Stored as an ArrayField to avoid joining to the
    # country table every time we retrieve sample(s).
    country = models.CharField(max_length=100, blank=True, null=True)

    # Free-text field; stored as an ArrayField to avoid joining to the
    # regions table every time we retrieve sample(s).
    regions = ArrayField(models.CharField(max_length=100, blank=True),
                         blank=True,
                         null=True)

    # Free-text field; stored as an ArrayField to avoid joining to the
    # reference table every time we retrieve sample(s)
    references = ArrayField(models.CharField(max_length=100, blank=True),
                            blank=True,
                            null=True)


    # Free text field with no validation;
    collector_name = models.CharField(max_length=50, blank=True, null=True)

    # Unused; here for backward compatibility
    collector_id = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     db_column='collector_id',
                                     related_name='+',
                                     blank=True,
                                     null=True)

    # Unused; here for backward compatibility
    sesar_number = models.CharField(max_length=9, blank=True, null=True)

    class Meta:
        db_table = 'samples'


class SubsampleType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(unique=True, max_length=100)

    class Meta:
        db_table = 'subsample_types'


class Subsample(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    version = AutoIncVersionField()
    sample = models.ForeignKey(Sample)
    public_data = models.BooleanField(default=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    subsample_type = models.ForeignKey(SubsampleType)

    class Meta:
        db_table = 'subsamples'


class Grid(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = AutoIncVersionField()
    subsample = models.ForeignKey(Subsample)
    width = models.SmallIntegerField()
    height = models.SmallIntegerField()
    public_data = models.BooleanField(default=False)

    class Meta:
        db_table = 'grids'


class MetamorphicGrade(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(unique=True, max_length=100)

    class Meta:
        db_table = 'metamorphic_grades'


class MetamorphicRegion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(unique=True, max_length=100)
    shape = models.GeometryField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    label_location = models.GeometryField(blank=True, null=True)

    class Meta:
        db_table = 'metamorphic_regions'


class Mineral(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # real_mineral is supposed to be NOT NULL, but it's not possible to run
    # the migration with that restriction, so here we go; this can be fixed
    # once the app goes into production.
    real_mineral = models.ForeignKey('self',
                                     blank=True,
                                     null=True)
    name = models.CharField(unique=True, max_length=100)

    class Meta:
        db_table = 'minerals'


class SampleMineral(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sample = models.ForeignKey(Sample)
    mineral = models.ForeignKey(Mineral)
    amount = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        db_table = 'sample_minerals'


# Following are models for easy retrieval of sample-related free-text fields
# from the database.
#
# Though each of these are stored as an ArrayField instances on the samples
# table, the search interface requires a list of all them to filter against;
# we can use these models to accomplish that without an expensive query on the
# the relevant columns of the samples table.
#
# Now, admittedly, this is a denormalization, but I feel that this is a
# reasonable trade-off to get faster GET requests, which is what this
# application will do most of the time.


class Country(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(unique=True, max_length=100)

    class Meta:
        db_table = 'countries'


class Region(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(unique=True, max_length=100)

    class Meta:
        db_table = 'regions'


class Reference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(unique=True, max_length=100)

    class Meta:
        db_table = 'references'


class Collector(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(unique=True, max_length=50)

    class Meta:
        db_table = 'collectors'
