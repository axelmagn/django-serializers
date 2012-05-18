from serializers import DumpDataSerializer
from django.core.serializers.pyyaml import Deserializer


class Serializer(DumpDataSerializer):
    class Meta(DumpDataSerializer.Meta):
        format = 'yaml'
