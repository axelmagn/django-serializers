from serializers import DumpDataSerializer


class Serializer(DumpDataSerializer):
    class Meta(DumpDataSerializer.Meta):
        format = 'json'

Deserializer = Serializer
