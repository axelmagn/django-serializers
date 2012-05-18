from serializers import DumpDataSerializer


class JSONDumpDataSerializer(DumpDataSerializer):
    class Meta(DumpDataSerializer.Meta):
        format = 'json'


class YAMLDumpDataSerializer(DumpDataSerializer):
    class Meta(DumpDataSerializer.Meta):
        format = 'yaml'


class XMLDumpDataSerializer(DumpDataSerializer):
    class Meta(DumpDataSerializer.Meta):
        format = 'xml'
