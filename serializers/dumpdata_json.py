from serializers import DumpDataSerializer
from django.core.serializers.json import Deserializer


class Serializer(DumpDataSerializer):
    class Meta(DumpDataSerializer.Meta):
        format = 'json'
