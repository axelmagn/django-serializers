from serializers import FixtureSerializer

format = 'python'


class Serializer(FixtureSerializer):
    internal_use_only = True  # Backwards compatability

    def serialize(self, *args, **kwargs):
        return super(Serializer, self).serialize(format, *args, **kwargs)


def Deserializer(*args, **kwargs):
    return Serializer().deserialize(format, *args, **kwargs)
