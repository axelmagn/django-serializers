from serializers import DumpDataSerializer


class JSONDumpDataSerializer(DumpDataSerializer):
    class Meta(DumpDataSerializer.Meta):
        format = 'json'
