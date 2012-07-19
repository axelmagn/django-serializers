from django.db import models
from django.utils.encoding import smart_unicode
from serializers import Field, PrimaryKeyRelatedField, NaturalKeyRelatedField
from serializers import ModelSerializer
from serializers.renderers import (
    JSONRenderer,
    YAMLRenderer,
    DumpDataXMLRenderer
)
from serializers.parsers import (
    JSONParser,
    DumpDataXMLParser
)


class PrimaryKeyOrNaturalKeyRelatedField(PrimaryKeyRelatedField):
    """
    Serializes to either pk or natural key, depending on if 'use_natural_keys'
    is specified when calling `serialize()`.
    """
    def __init__(self, *args, **kwargs):
        self.nk_field = NaturalKeyRelatedField()
        self.pk_field = PrimaryKeyRelatedField()
        super(PrimaryKeyOrNaturalKeyRelatedField, self).__init__(*args, **kwargs)

    def convert_field(self, obj, field_name):
        if self.root.use_natural_keys:
            self.is_natural_key = True
            return self.nk_field.convert_field(obj, field_name)
        self.is_natural_key = False
        return self.pk_field.convert_field(obj, field_name)

    def revert_field(self, data, field_name, into):
        value = data.get(field_name)
        if hasattr(self.field.rel.to._default_manager, 'get_by_natural_key') and hasattr(value, '__iter__'):
            self.nk_field.field = self.field  # Total hack
            return self.nk_field.revert_field(data, field_name, into)
        return self.pk_field.revert_field(data, field_name, into)


class ModelNameField(Field):
    """
    Serializes the model instance's model name.  Eg. 'auth.User'.
    """
    def convert_field(self, obj, field_name):
        return smart_unicode(obj._meta)

    def revert_field(self, data, field_name, into):
        # We don't actually want to restore the model name metadata to a field.
        pass


class FixtureFields(ModelSerializer):
    _use_sorted_dict = False  # Ensure byte-for-byte backwards compatability

    class Meta:
        model_field_types = ('local_fields', 'many_to_many')

    def get_related_field(self, model_field):
        return PrimaryKeyOrNaturalKeyRelatedField()

    def revert_object(self, object_attrs, object_cls):
        return object_attrs


class FixtureSerializer(ModelSerializer):
    """
    A serializer that is intended to produce dumpdata formatted structures.
    """
    _use_sorted_dict = False  # Ensure byte-for-byte backwards compatability

    pk = Field()
    model = ModelNameField()
    fields = FixtureFields(is_root=True)

    class Meta:
        renderer_classes = {
            'xml': DumpDataXMLRenderer,
            'json': JSONRenderer,
            'yaml': YAMLRenderer,
        }
        parser_classes = {
            'xml': DumpDataXMLParser,
            'json': JSONParser
        }

    def default_fields(self, obj, cls, nested):
        return {}

    def revert_class(self, data):
        # TODO: ValidationError (DeserializationError?) if this fails
        return models.get_model(*data['model'].split("."))

    def serialize(self, *args, **kwargs):
        self.use_natural_keys = kwargs.pop('use_natural_keys', False)
        return super(FixtureSerializer, self).serialize(*args, **kwargs)
