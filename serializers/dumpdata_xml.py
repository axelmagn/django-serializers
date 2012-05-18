from serializers import DumpDataSerializer
from django.core.serializers.xml_serializer import Deserializer


class Serializer(DumpDataSerializer):
    class Meta(DumpDataSerializer.Meta):
        format = 'xml'
