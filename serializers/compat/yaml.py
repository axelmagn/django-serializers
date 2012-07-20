from serializers import FixtureSerializer


class Serializer(FixtureSerializer):
    class Meta(FixtureSerializer.Meta):
        format = 'yaml'

Deserializer = Serializer
