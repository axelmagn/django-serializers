from serializers import DumpDataSerializer
from django.core.serializers.python import Deserializer


class Serializer(DumpDataSerializer):
    internal_use_only = True  # Backwards compatability
