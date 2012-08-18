from serializers import FixtureSerializer
from serializers import serialize, deserialize

format = 'json'


class Serializer(FixtureSerializer):
    internal_use_only = False  # Backwards compatability

    def getvalue(self):
        return self.value  # Backwards compatability with serialization API.

    def serialize(self, *args, **kwargs):
        self.value = serialize(format, *args, **kwargs)
        return self.value


def Deserializer(*args, **kwargs):
    return deserialize(format, *args, **kwargs)
