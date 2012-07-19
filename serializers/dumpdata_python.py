from serializers import FixtureSerializer


class Serializer(FixtureSerializer):
    internal_use_only = True  # Backwards compatability

Deserializer = Serializer
