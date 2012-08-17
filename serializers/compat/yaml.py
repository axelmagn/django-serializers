from serializers import FixtureSerializer

format = 'yaml'


class Serializer(FixtureSerializer):
    def serialize(self, *args, **kwargs):
        return super(Serializer, self).serialize(format, *args, **kwargs)


def Deserializer(*args, **kwargs):
    return Serializer().deserialize(format, *args, **kwargs)
