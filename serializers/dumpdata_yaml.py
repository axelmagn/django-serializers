from serializers import DumpDataSerializer


class Serializer(DumpDataSerializer):
    class Meta(DumpDataSerializer.Meta):
        format = 'yaml'

Deserializer = Serializer
