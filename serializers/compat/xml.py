from serializers import FixtureSerializer


class Serializer(FixtureSerializer):
    def serialize(self, *args, **kwargs):
        kwargs['format'] = 'xml'
        return super(Serializer, self).serialize(*args, **kwargs)

    def deserialize(self, *args, **kwargs):
        kwargs['format'] = 'xml'
        return super(Serializer, self).deserialize(*args, **kwargs)

Deserializer = Serializer
