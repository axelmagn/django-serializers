from serializers import FixtureSerializer

format = 'json'


class Serializer(FixtureSerializer):
    internal_use_only = False  # Backwards compatability

    def getvalue(self):
        return self.value  # Backwards compatability with serialization API.

    def serialize(self, *args, **kwargs):
        return super(Serializer, self).serialize(format, *args, **kwargs)


def Deserializer(*args, **kwargs):
    return Serializer().deserialize(format, *args, **kwargs)
