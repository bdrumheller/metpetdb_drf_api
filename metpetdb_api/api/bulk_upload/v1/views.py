from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from api.chemical_analyses.lib.query import chemical_analysis_query
from api.lib.permissions import IsOwnerOrReadOnly, IsSuperuserOrReadOnly
from api.lib.query import sample_qs_optimizer, chemical_analyses_qs_optimizer

from api.samples.lib.query import sample_query
from api.samples.v1.serializers import (
    SampleSerializer,
    RockTypeSerializer,
    MineralSerializer,
    RegionSerializer,
    ReferenceSerializer,
    CollectorSerializer,
    SubsampleSerializer,
    MetamorphicRegionSerializer,
    MetamorphicGradeSerializer,
    SubsampleTypeSerializer,
)
from apps.chemical_analyses.models import ChemicalAnalysis
from apps.samples.models import (
    Country,
    Sample,
    RockType,
    Mineral,
    Region,
    Reference,
    Collector,
    Subsample,
    MetamorphicRegion,
    MetamorphicGrade,
    SampleMineral,
    GeoReference,
    SubsampleType,
)

from api.bulk_upload.v1 import upload_templates
import json
import sys
import urllib.request
from csv import reader


class Parser:
    def __init__(self, template):
        self.template = template #create new template object here
    
    def line_split(self, content):
        data = content.decode('utf-8').split('\r\n')[:-1]
        if len(data) < 2: data = content.decode('utf-8').split('\n')[:-1]
        if len(data) < 2: print ('ERROR: no data entries'); #return error    
        lined = [] # line separated data
        for entry in reader(data): lined.append(entry)
        return lined

    # Effects: Generates JSON file from passed template
    def parse(self, url):   
        #try to open the file
        try:
            url = url[:-1] +'1'
            content = urllib.request.urlopen(url).read()
            lined = self.line_split(content)
            print(self.template.parse(lined))
            return  self.template.parse(lined) # return the JSON ready file

        except:
            print ('ERROR: Unable to open file {0} for reading.'.format(url))
            #exit(1) TODO return the error
        
            
##############################################################
# Effects: writes json formatted JSON to output_file_name    #
#          out.JSON if no file is specified                  #
##############################################################
def write_JSON(JSON, output_file_name='out.JSON'):
    json_data = json.dumps(JSON)
    try: 
        #output_file = open(output_file_name, 'w+')
        #output_file.write(json_data)
        #output_file.close()
        print (json_data)
    except:
        print ("ERROR: unable to write JSON to file {0}".format(output_file_name))


class BulkUploadSampleViewSet(viewsets.ModelViewSet):
    queryset = Sample.objects.all()
    serializer_class = SampleSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsOwnerOrReadOnly,)
    http_method_names=['post'] 

    def _handle_metamorphic_regions(self, instance, ids):
        metamorphic_regions = []
        for id in ids:
            try:
                metamorphic_region = MetamorphicRegion.objects.get(pk=id)
            except:
                raise ValueError('Invalid metamorphic_region id: {}'
                                 .format(id))
            else:
                metamorphic_regions.append(metamorphic_region)
        instance.metamorphic_regions = metamorphic_regions


    def _handle_metamorphic_grades(self, instance, ids):
        metamorphic_grades = []
        for id in ids:
            try:
                metamorphic_grade = MetamorphicGrade.objects.get(pk=id)
            except:
                raise ValueError('Invalid metamorphic_grade id: {}'.format(id))
            else:
                metamorphic_grades.append(metamorphic_grade)
        instance.metamorphic_grades = metamorphic_grades


    def _handle_minerals(self, instance, minerals):
        to_add = []
        for record in minerals:
            try:
                to_add.append(
                    {'mineral': Mineral.objects.get(pk=record['id']),
                     'amount': record['amount']})
            except Mineral.DoesNotExist:
                raise ValueError('Invalid mineral id: {}'.format(record['id']))

        SampleMineral.objects.filter(sample=instance).delete()
        for record in to_add:
            SampleMineral.objects.create(sample=instance,
                                         mineral=record['mineral'],
                                         amount=record['amount'])


    def _handle_references(self, instance, references):
        to_add = []

        georefences = GeoReference.objects.filter(name__in=references)
        to_add.extend(georefences)

        missing_georefs = (set(references) -
                           set([georef.name for georef in georefences]))
        if missing_georefs:
            new_georefs = GeoReference.objects.bulk_create(
                [GeoReference(name=name) for name in missing_georefs]
            )
            Reference.objects.bulk_create([Reference(name=name)
                                           for name in missing_georefs])
            to_add.extend(new_georefs)

        # FIXME: this is lazy; we should ideally clear only those
        # associations that aren't needed anymore and create new
        # associations, if required.
        instance.references.clear()
        instance.references.add(*to_add)


    def perform_create(self, serializer):
        return serializer.save()


    def create(self, request, *args, **kwargs):
        print (request.data)
        serializer = self.get_serializer(data=request.data)
        url = request.data.get('url')
        template_name = request.data.get('template')
        template_instance = ''

        #Dynamically generate instance of template
        try:
            module = upload_templates
            class_ = getattr(module, template_name)
            template_instance = class_()
        except:
            return Response(
                data = {'error': 'Invalid template {0}'.format(template_name)},
                status=400
            )

        p = Parser(template_instance) 
        JSON = p.parse(url)
        write_JSON(JSON)        

        return Response(JSON)
        
        print("parsed")

        #TODO change the serial validator
        serializer.is_valid(raise_exception=True)
        
        
        
        instance = self.perform_create(serializer)

        metamorphic_region_ids = request.data.get('metamorphic_region_ids')
        metamorphic_grade_ids = request.data.get('metamorphic_grade_ids')
        minerals = request.data.get('minerals')
        references = request.data.get('references')

        if metamorphic_region_ids:
            try:
                self._handle_metamorphic_regions(instance,
                                                 metamorphic_region_ids)
            except ValueError as err:
                return Response(
                    data={'error': err.args},
                    status=400
                )

        if metamorphic_grade_ids:
            try:
                self._handle_metamorphic_grades(instance,
                                                metamorphic_grade_ids)
            except ValueError as err:
                return Response(
                    data={'error': err.args},
                    status=400
                )

        if minerals:
            try:
                self._handle_minerals(instance, minerals)
            except ValueError as err:
                return Response(
                    data={'error': err.args},
                    status=400
                )

        if references:
            self._handle_references(instance, references)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data,
                        status=status.HTTP_201_CREATED,
                        headers=headers)


class SubsampleViewSet(viewsets.ModelViewSet):
    queryset = Subsample.objects.all()
    serializer_class = SubsampleSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsOwnerOrReadOnly,)


class SubsampleTypeViewSet(viewsets.ModelViewSet):
    queryset = SubsampleType.objects.all()
    serializer_class = SubsampleTypeSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsSuperuserOrReadOnly,)


class RockTypeViewSet(viewsets.ModelViewSet):
    queryset = RockType.objects.all()
    serializer_class = RockTypeSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsSuperuserOrReadOnly,)


class MineralViewSet(viewsets.ModelViewSet):
    queryset = Mineral.objects.all()
    serializer_class = MineralSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsSuperuserOrReadOnly,)


class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsSuperuserOrReadOnly,)


class ReferenceViewSet(viewsets.ModelViewSet):
    queryset = Reference.objects.all()
    serializer_class = ReferenceSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsSuperuserOrReadOnly,)


class CollectorViewSet(viewsets.ModelViewSet):
    queryset = Collector.objects.all()
    serializer_class = CollectorSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsSuperuserOrReadOnly,)


class MetamorphicRegionViewSet(viewsets.ModelViewSet):
    queryset = MetamorphicRegion.objects.all()
    serializer_class = MetamorphicRegionSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsSuperuserOrReadOnly,)


class MetamorphicGradeViewSet(viewsets.ModelViewSet):
    queryset = MetamorphicGrade.objects.all()
    serializer_class = MetamorphicGradeSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsSuperuserOrReadOnly,)


class GeoReferenceViewSet(viewsets.ModelViewSet):
    queryset = MetamorphicRegion.objects.all()
    serializer_class = MetamorphicRegionSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsSuperuserOrReadOnly,)


class SampleNumbersView(APIView):
    def get(self, request, format=None):
        sample_numbers = (
            Sample
            .objects
            .all()
            .values_list('number', flat=True)
            .distinct()
        )
        return Response({'sample_numbers': sample_numbers})


class CountryNamesView(APIView):
    def get(self, request, format=None):
        country_names = (
            Country
            .objects
            .all()
            .values_list('name', flat=True)
            .distinct()
        )
        return Response({'country_names': country_names})


class SampleOwnerNamesView(APIView):
    def get(self, request, format=None):
        sample_owner_names = (
            Sample
            .objects
            .all()
            .values_list('owner__name', flat=True)
            .distinct()
        )
        return Response({'sample_owner_names': sample_owner_names})
