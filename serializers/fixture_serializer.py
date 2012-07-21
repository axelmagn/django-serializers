from django.db import models
from django.utils.datastructures import SortedDict
from django.utils.encoding import smart_unicode
from serializers import Field, PrimaryKeyRelatedField, NaturalKeyRelatedField
from serializers import Serializer, ModelSerializer
from serializers.renderers import (
    JSONRenderer,
    YAMLRenderer,
    DumpDataXMLRenderer
)
from serializers.parsers import (
    JSONParser,
    DumpDataXMLParser
)
from serializers.utils import DictWithMetadata


class PrimaryKeyOrNaturalKeyRelatedField(PrimaryKeyRelatedField):
    """
    Serializes to either pk or natural key, depending on if 'use_natural_keys'
    is specified when calling `serialize()`.
    """

    def __init__(self, *args, **kwargs):
        self.nk_field = NaturalKeyRelatedField()
        self.pk_field = PrimaryKeyRelatedField()
        super(PrimaryKeyOrNaturalKeyRelatedField, self).__init__(*args, **kwargs)

    def field_to_native(self, obj, field_name):
        if self.root.use_natural_keys:
            self.is_natural_key = True
            return self.nk_field.field_to_native(obj, field_name)
        self.is_natural_key = False
        return self.pk_field.field_to_native(obj, field_name)

    def field_from_native(self, data, field_name, into):
        value = data.get(field_name)
        if hasattr(self.model_field.rel.to._default_manager, 'get_by_natural_key') and hasattr(value, '__iter__'):
            self.nk_field.model_field = self.model_field  # Total hack
            return self.nk_field.field_from_native(data, field_name, into)
        return self.pk_field.field_from_native(data, field_name, into)


class ModelNameField(Field):
    """
    Serializes the model instance's model name.  Eg. 'auth.User'.
    """
    def field_to_native(self, obj, field_name):
        return smart_unicode(obj._meta)

    def field_from_native(self, data, field_name, into):
        # We don't actually want to restore the model name metadata to a field.
        pass


class FixtureFields(Serializer):
    _dict_class = DictWithMetadata  # Unsorted dict to ensure byte-for-byte backwards compatability

    class Meta:
        model_field_types = ('local_fields', 'many_to_many')

    def default_fields(self, obj, cls, nested):
        """
        Return the set of all fields defined on the model.
        """
        if obj is not None:
            cls = obj.__class__

        # all local fields + all m2m fields without through relationship
        opts = cls._meta.concrete_model._meta
        fields = [field for field in opts.local_fields if field.serialize]
        fields += [field for field in opts.many_to_many
                   if field.serialize and field.rel.through._meta.auto_created]

        ret = SortedDict()
        for model_field in fields:
            if model_field.rel and nested:
                field = FixtureSerializer()
            elif model_field.rel:
                field = PrimaryKeyOrNaturalKeyRelatedField()
            else:
                field = Field()
            field.initialize(parent=self, model_field=model_field)
            ret[model_field.name] = field
        return ret


class FixtureSerializer(ModelSerializer):
    """
    A serializer that is intended to produce dumpdata formatted structures.
    """
    _dict_class = DictWithMetadata  # Unsorted dict to ensure byte-for-byte backwards compatability

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
