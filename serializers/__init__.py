from serializers.serializer import (
    Serializer,
    ModelSerializer,
)
from serializers.fields import (
    Field,
    RelatedField,
    PrimaryKeyRelatedField,
    NaturalKeyRelatedField,
)
from serializers.renderers import (
    XMLRenderer,
    JSONRenderer,
    YAMLRenderer,
    CSVRenderer,
    HTMLRenderer,
    DumpDataXMLRenderer
)
from serializers.parsers import (
    JSONParser,
    DumpDataXMLParser
)
from serializers.fixture_serializer import FixtureSerializer

__version__ = '0.6.0'


def serialize(format, obj, serializer=FixtureSerializer, **options):
    renderer_classes = {
        'xml': XMLRenderer,
        'json': JSONRenderer,
        'yaml': YAMLRenderer,
        'csv': CSVRenderer,
        'html': HTMLRenderer,
        'python': None
    }
    # TODO: Remove distinction between fixture xml and regular xml
    if issubclass(serializer, FixtureSerializer):
        renderer_classes['xml'] = DumpDataXMLRenderer

    kwargs = {}
    for key in 'fields', 'exclude', 'use_natural_keys':
        if key in options.keys():
            kwargs[key] = options.pop(key)

    renderer = renderer_classes[format]
    data = serializer(instance=obj, **kwargs).data
    if renderer:
        return renderer().render(data, **options)
    return data


def deserialize(format, stream, serializer=FixtureSerializer, **options):
    parser_classes = {
        'xml': DumpDataXMLParser,
        'json': JSONParser,
        'python': None
    }

    parser = parser_classes[format]

    if parser:
        data = parser().parse(stream, **options)
    else:
        data = stream

    return serializer(data).object
