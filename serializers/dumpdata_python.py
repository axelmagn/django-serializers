from serializers import DumpDataSerializer


class Serializer(DumpDataSerializer):
    internal_use_only = True  # Backwards compatability

Deserializer = Serializer
