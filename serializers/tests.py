import datetime
from decimal import Decimal
from django.core import serializers
from django.db import models
from django.test import TestCase
from django.utils.datastructures import SortedDict
from serializers import Serializer, ModelSerializer, FixtureSerializer
from serializers.fields import Field, NaturalKeyRelatedField, PrimaryKeyRelatedField
from serializers import serialize, deserialize
from serializers import fields
from serializers.serializer import _is_protected_type


class Comment(object):
    def __init__(self, username, content, created):
        self.username = username
        self.content = content
        self.created = created or datetime.datetime.now()

    def __eq__(self, other):
        return all([getattr(self, attr) == getattr(other, attr)
                    for attr in ('username', 'content', 'created')])


class CommentSerializer(Serializer):
    username = fields.CharField(max_length=20)
    content = fields.CharField(max_length=1000)
    created = fields.DateTimeField()

    def restore_object(self, data, instance=None):
        if instance is None:
            return Comment(**data)
        for key, val in data.items():
            setattr(instance, key, val)
        return instance


class BasicTests(TestCase):
    def setUp(self):
        self.comment = Comment(
            'tomchristie',
            'Happy new year!',
            datetime.datetime(2012, 1, 1)
        )
        self.data = {
            'username': 'tomchristie',
            'content': 'Happy new year!',
            'created': datetime.datetime(2012, 1, 1)
        }

    def test_empty(self):
        serializer = CommentSerializer()
        expected = {
            'username': '',
            'content': '',
            'created': None
        }
        self.assertEquals(serializer.data, expected)

    def test_serialization(self):
        serializer = CommentSerializer(instance=self.comment)
        expected = self.data
        self.assertEquals(serializer.data, expected)

    def test_deserialization_for_create(self):
        serializer = CommentSerializer(self.data)
        expected = self.comment
        self.assertEquals(serializer.is_valid(), True)
        self.assertEquals(serializer.object, expected)
        self.assertFalse(serializer.object is expected)

    def test_deserialization_for_update(self):
        serializer = CommentSerializer(self.data, instance=self.comment)
        expected = self.comment
        self.assertEquals(serializer.is_valid(), True)
        self.assertEquals(serializer.object, expected)
        self.assertTrue(serializer.object is expected)


class ValidationTests(TestCase):
    def setUp(self):
        self.comment = Comment(
            'tomchristie',
            'Happy new year!',
            datetime.datetime(2012, 1, 1)
        )
        self.data = {
            'username': 'x' * 100,
            'content': 'Happy new year!',
            'created': datetime.datetime(2012, 1, 1)
        }

    def test_deserialization_for_create(self):
        serializer = CommentSerializer(self.data)
        self.assertEquals(serializer.is_valid(), False)
        self.assertEquals(serializer.errors, {'username': [u'Ensure this value has at most 20 characters (it has 100).']})

    def test_deserialization_for_update(self):
        serializer = CommentSerializer(self.data, instance=self.comment)
        self.assertEquals(serializer.is_valid(), False)
        self.assertEquals(serializer.errors, {'username': [u'Ensure this value has at most 20 characters (it has 100).']})


class MetadataTests(TestCase):
    # def setUp(self):
    #     self.comment = Comment(
    #         'tomchristie',
    #         'Happy new year!',
    #         datetime.datetime(2012, 1, 1)
    #     )
    #     self.data = {
    #         'username': 'tomchristie',
    #         'content': 'Happy new year!',
    #         'created': datetime.datetime(2012, 1, 1)
    #     }

    def test_empty(self):
        serializer = CommentSerializer()
        expected = {
            'username': fields.CharField,
            'content': fields.CharField,
            'created': fields.DateTimeField
        }
        for field_name, field in expected.items():
            self.assertTrue(isinstance(serializer.data.fields[field_name], field))

###########################################################################
#
#
#


# ObjectSerializer has been removed from serializers
# leaving it in the tests for the moment for more coverage.

class ObjectSerializer(Serializer):
    def default_fields(self, serialize, obj=None, data=None, nested=False):
        """
        Given an object, return the default set of fields to serialize.

        For ObjectSerializer this should be the set of all the non-private
        object attributes.
        """
        if not serialize:
            raise Exception('ObjectSerializer does not support deserialization')

        ret = SortedDict()
        attrs = [key for key in obj.__dict__.keys() if not(key.startswith('_'))]
        for attr in sorted(attrs):
            if nested:
                field = self.__class__()
            else:
                field = Field()
            field.initialize(parent=self)
            ret[attr] = field
        return ret

    def to_native(self, obj):
        if _is_protected_type(obj):
            return obj
        return super(ObjectSerializer, self).to_native(obj)

class NestedObjectSerializer(ObjectSerializer):
    class Meta:
        nested = True


class DepthOneObjectSerializer(ObjectSerializer):
    class Meta:
        nested = 1


def expand(obj):
    """
    Unroll any generators in returned object.
    """
    if isinstance(obj, dict):
        ret = SortedDict()  # Retain original ordering
        for key, val in obj.items():
            ret[key] = expand(val)
        return ret
    elif hasattr(obj, '__iter__'):
        return [expand(item) for item in obj]
    return obj


def get_deserialized(queryset, serializer=None, format=None, **kwargs):
    format = format or 'json'
    if serializer:
        # django-serializers
        serialized = serialize(format, queryset, serializer=serializer, **kwargs)
        return deserialize(format, serialized, serializer=serializer)
    # Existing Django serializers
    serialized = serializers.serialize(format, queryset, **kwargs)
    return serializers.deserialize(format, serialized)


def deserialized_eq(objects1, objects2):
    objects1 = list(objects1)
    objects2 = list(objects2)
    if len(objects1) != len(objects2):
        return False
    for index in range(len(objects1)):
        if objects1[index].object != objects2[index].object:
            return False
        if objects1[index].m2m_data.keys() != objects2[index].m2m_data.keys():
            return False
        m2m_data1 = objects1[index].m2m_data
        m2m_data2 = objects2[index].m2m_data
        for field_name in m2m_data1.keys():
            if set([int(m2m) for m2m in m2m_data1[field_name]]) != \
                set([int(m2m) for m2m in m2m_data2[field_name]]):
                return False
        object1 = objects1[index].object
        object2 = objects2[index].object
        for field in object1._meta.fields:
            if getattr(object1, field.attname) != getattr(object2, field.attname):
                return False

    return True


class SerializationTestCase(TestCase):
    def assertEquals(self, lhs, rhs):
        """
        Regular assert, but unroll any generators before comparison.
        """
        lhs = expand(lhs)
        rhs = expand(rhs)
        return super(SerializationTestCase, self).assertEquals(lhs, rhs)


class TestBasicObjects(SerializationTestCase):
    def test_list(self):
        obj = []
        expected = '[]'
        output = serialize('json', obj, serializer=ObjectSerializer)
        self.assertEquals(output, expected)

    def test_dict(self):
        obj = {}
        expected = '{}'
        output = serialize('json', obj, serializer=ObjectSerializer)
        self.assertEquals(output, expected)


class ExampleObject(object):
    """
    An example class for testing basic serialization.
    """
    def __init__(self):
        self.a = 1
        self.b = 'foo'
        self.c = True
        self._hidden = 'other'


class Person(object):
    """
    An example class for testing serilization of properties and methods.
    """
    CHILD_AGE = 16

    def __init__(self, first_name=None, last_name=None, age=None, **kwargs):
        self.first_name = first_name
        self.last_name = last_name
        self.age = age
        for key, val in kwargs.items():
            setattr(self, key, val)

    @property
    def full_name(self):
        return self.first_name + ' ' + self.last_name

    def is_child(self):
        return self.age < self.CHILD_AGE

    def __unicode__(self):
        return self.full_name


class EncoderTests(SerializationTestCase):
    def setUp(self):
        self.obj = ExampleObject()

    def test_json(self):
        expected = '{"a": 1, "b": "foo", "c": true}'
        output = serialize('json', self.obj, serializer=ObjectSerializer)
        self.assertEquals(output, expected)

    def test_yaml(self):
        expected = '{a: 1, b: foo, c: true}\n'
        output = serialize('yaml', self.obj, serializer=ObjectSerializer)
        self.assertEquals(output, expected)

    def test_xml(self):
        expected = '<?xml version="1.0" encoding="utf-8"?>\n<object><a>1</a><b>foo</b><c>True</c></object>'
        output = serialize('xml', self.obj, serializer=ObjectSerializer)
        self.assertEquals(output, expected)


class BasicSerializerTests(SerializationTestCase):
    def setUp(self):
        self.obj = ExampleObject()

    def test_serialize_basic_object(self):
        """
        Objects are serialized by converting into dictionaries.
        """
        expected = {
            'a': 1,
            'b': 'foo',
            'c': True
        }

        self.assertEquals(serialize('python', self.obj, serializer=ObjectSerializer), expected)

    def test_serialize_fields(self):
        """
        Setting 'Meta.fields' specifies exactly which fields to serialize.
        """
        class CustomSerializer(ObjectSerializer):
            class Meta:
                fields = ('a', 'c')

        expected = {
            'a': 1,
            'c': True
        }

        self.assertEquals(serialize('python', self.obj, serializer=CustomSerializer), expected)

    def test_serialize_exclude(self):
        """
        Setting 'Meta.exclude' causes a field to be excluded.
        """
        class CustomSerializer(ObjectSerializer):
            class Meta:
                exclude = ('b',)

        expected = {
            'a': 1,
            'c': True
        }

        self.assertEquals(serialize('python', self.obj, serializer=CustomSerializer), expected)


class SerializeAttributeTests(SerializationTestCase):
    """
    Test covering serialization of different types of attributes on objects.
    """
    def setUp(self):
        self.obj = Person('john', 'doe', 42)

    def test_serialization_only_includes_instance_properties(self):
        """
        By default only serialize instance properties, not class properties.
        """
        expected = {
            'first_name': 'john',
            'last_name': 'doe',
            'age': 42
        }

        self.assertEquals(serialize('python', self.obj, serializer=ObjectSerializer), expected)

    def test_serialization_can_include_properties(self):
        """
        Object properties can be included as fields.
        """
        class CustomSerializer(ObjectSerializer):
            full_name = Field()

            class Meta:
                fields = ('full_name', 'age')

        expected = {
            'full_name': 'john doe',
            'age': 42
        }

        self.assertEquals(serialize('python', self.obj, serializer=CustomSerializer), expected)

    def test_serialization_can_include_no_arg_methods(self):
        """
        Object methods may be included as fields.
        """
        class CustomSerializer(ObjectSerializer):
            full_name = Field()
            is_child = Field()

            class Meta:
                fields = ('full_name', 'is_child')

        expected = {
            'full_name': 'john doe',
            'is_child': False
        }

        self.assertEquals(serialize('python', self.obj, serializer=CustomSerializer), expected)


class SerializerFieldTests(SerializationTestCase):
    """
    Tests declaring explicit fields on the serializer.
    """

    def setUp(self):
        self.obj = Person('john', 'doe', 42)

    def test_explicit_fields_replace_defaults(self):
        """
        Setting include_default_fields to `False` fields on a serializer
        ensures that only explicitly declared fields are used.
        """
        class CustomSerializer(Serializer):
            full_name = ObjectSerializer()

        expected = {
            'full_name': 'john doe',
        }

        self.assertEquals(serialize('python', self.obj, serializer=CustomSerializer), expected)

    def test_include_default_fields(self):
        """
        By default, both fields which have been explicitly included via a
        Serializer field declaration, and regular default object fields will
        be included.
        """
        class CustomSerializer(ObjectSerializer):
            full_name = ObjectSerializer()

        expected = {
            'full_name': 'john doe',
            'first_name': 'john',
            'last_name': 'doe',
            'age': 42
        }

        self.assertEquals(serialize('python', self.obj, serializer=CustomSerializer), expected)

    # def test_field_label(self):
    #     """
    #     A serializer field can take a 'label' argument, which is used as the
    #     field key instead of the field's property name.
    #     """
    #     class CustomSerializer(ObjectSerializer):
    #         full_name = ObjectSerializer(label='Full name')
    #         age = ObjectSerializer(label='Age')

    #         class Meta:
    #             fields = ('full_name', 'age')

    #     expected = {
    #         'Full name': 'john doe',
    #         'Age': 42
    #     }

    #     self.assertEquals(serialize('python', self.obj, serializer=CustomSerializer), expected)

    def test_source(self):
        """
        Setting source='*', means the complete object will be used when
        serializing that field.
        """
        class CustomSerializer(ObjectSerializer):
            full_name = ObjectSerializer()
            details = ObjectSerializer(source='*')

            class Meta:
                fields = ('full_name', 'details')

        expected = {
            'full_name': 'john doe',
            'details': {
                'first_name': 'john',
                'last_name': 'doe',
                'age': 42
            }
        }

        self.assertEquals(serialize('python', self.obj, serializer=CustomSerializer), expected)

    def test_source_all_with_custom_serializer(self):
        """
        A custom serializer can be used with source='*' as serialize the
        complete object within a field.
        """
        class DetailsSerializer(ObjectSerializer):
            first_name = ObjectSerializer()
            last_name = ObjectSerializer()

            class Meta:
                fields = ('first_name', 'last_name')

        class CustomSerializer(ObjectSerializer):
            full_name = ObjectSerializer()
            details = DetailsSerializer(source='*')

            class Meta:
                fields = ('full_name', 'details')

        expected = {
            'full_name': 'john doe',
            'details': {
                'first_name': 'john',
                'last_name': 'doe'
            }
        }

        self.assertEquals(serialize('python', self.obj, serializer=CustomSerializer), expected)

    # def test_serializer_fields_do_not_share_state(self):
    #     """
    #     Make sure that different serializer instances do not share the same
    #     SerializerField instances.
    #     """
    #     class CustomSerializer(Serializer):
    #         example = Serializer()

    #     serializer_one = CustomSerializer()
    #     serializer_two = CustomSerializer()
    #     self.assertFalse(serializer_one.fields['example'] is serializer_two.fields['example'])

    def test_serializer_field_order_preserved(self):
        """
        Make sure ordering of serializer fields is preserved.
        """
        class CustomSerializer(ObjectSerializer):
            first_name = Field()
            full_name = Field()
            age = Field()
            last_name = Field()

            class Meta:
                preserve_field_order = True

        keys = ['first_name', 'full_name', 'age', 'last_name']

        self.assertEquals(serialize('python', self.obj, serializer=CustomSerializer).keys(), keys)


class NestedSerializationTests(SerializationTestCase):
    """
    Tests serialization of nested objects.
    """

    def setUp(self):
        fred = Person('fred', 'bloggs', 41)
        emily = Person('emily', 'doe', 37)
        jane = Person('jane', 'doe', 44, partner=fred)
        self.obj = Person('john', 'doe', 42, siblings=[jane, emily])

    def test_nested_serialization(self):
        """
        Default with nested serializers is to include full serialization of
        child elements.
        """
        expected = {
            'first_name': 'john',
            'last_name': 'doe',
            'age': 42,
            'siblings': [
                {
                    'first_name': 'jane',
                    'last_name': 'doe',
                    'age': 44,
                    'partner': {
                        'first_name': 'fred',
                        'last_name': 'bloggs',
                        'age': 41,
                    }
                },
                {
                    'first_name': 'emily',
                    'last_name': 'doe',
                    'age': 37,
                }
            ]
        }
        self.assertEquals(serialize('python', self.obj, serializer=NestedObjectSerializer), expected)

    def test_nested_serialization_with_args(self):
        """
        We can pass serializer options through to nested fields as usual.
        """
        class SiblingsSerializer(ObjectSerializer):
            full_name = Field()

            class Meta:
                fields = ('full_name',)

        class PersonSerializer(Serializer):
            full_name = Field()
            siblings = SiblingsSerializer()

        expected = {
            'full_name': 'john doe',
            'siblings': [
                {
                    'full_name': 'jane doe'
                },
                {
                    'full_name': 'emily doe',
                }
            ]
        }

        self.assertEquals(serialize('python', self.obj, serializer=PersonSerializer), expected)

    # TODO: Changed slightly
    # def test_flat_serialization(self):
    #     """
    #     If 'nested' is False then nested objects should be serialized as
    #     flat values.
    #     """
    #     expected = {
    #         'first_name': 'john',
    #         'last_name': 'doe',
    #         'age': 42,
    #         'siblings': [
    #             'jane doe',
    #             'emily doe'
    #         ]
    #     }

    #     self.assertEquals(serialize('python', self.obj, serializer=ObjectSerializer), expected)

    def test_depth_one_serialization(self):
        """
        If 'nested' is greater than 0 then nested objects should be serialized
        as flat values once the specified depth has been reached.
        """
        expected = {
            'first_name': 'john',
            'last_name': 'doe',
            'age': 42,
            'siblings': [
                {
                    'first_name': 'jane',
                    'last_name': 'doe',
                    'age': 44,
                    'partner': 'fred bloggs'
                },
                {
                    'first_name': 'emily',
                    'last_name': 'doe',
                    'age': 37,
                }
            ]
        }

        self.assertEquals(serialize('python', self.obj, serializer=DepthOneObjectSerializer), expected)


class RecursiveSerializationTests(SerializationTestCase):
    def setUp(self):
        emily = Person('emily', 'doe', 37)
        john = Person('john', 'doe', 42, daughter=emily)
        emily.father = john
        self.obj = john

    def test_recursive_serialization(self):
        """
        If recursion occurs, serializer will fall back to flat values.
        """
        expected = {
            'first_name': 'john',
            'last_name': 'doe',
            'age': 42,
            'daughter': {
                    'first_name': 'emily',
                    'last_name': 'doe',
                    'age': 37,
                    'father': 'john doe'
            }
        }
        self.assertEquals(serialize('python', self.obj, serializer=NestedObjectSerializer), expected)


##### Simple models without relationships. #####

class RaceEntry(models.Model):
    name = models.CharField(max_length=100)
    runner_number = models.PositiveIntegerField()
    start_time = models.DateTimeField()
    finish_time = models.DateTimeField()


class RaceEntrySerializer(ModelSerializer):
    class Meta:
        model = RaceEntry


class TestSimpleModel(SerializationTestCase):
    def setUp(self):
        RaceEntry.objects.create(
            name='John doe',
            runner_number=6014,
            start_time=datetime.datetime(year=2012, month=4, day=30, hour=9),
            finish_time=datetime.datetime(year=2012, month=4, day=30, hour=12, minute=25)
        )

    def test_simple_dumpdata_json(self):
        self.assertEquals(
            serialize('json', RaceEntry.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('json', RaceEntry.objects.all())
        )

    def test_simple_dumpdata_yaml(self):
        self.assertEquals(
            serialize('yaml', RaceEntry.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('yaml', RaceEntry.objects.all())
        )

    def test_simple_dumpdata_xml(self):
        self.assertEquals(
            serialize('xml', RaceEntry.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('xml', RaceEntry.objects.all())
        )

    def test_csv(self):
        expected = (
            "id,name,runner_number,start_time,finish_time\r\n"
            "1,John doe,6014,2012-04-30 09:00:00,2012-04-30 12:25:00\r\n"
        )
        self.assertEquals(
            serialize('csv', RaceEntry.objects.all(), serializer=RaceEntrySerializer),
            expected
        )

    def test_simple_dumpdata_fields(self):
        self.assertEquals(
            serialize('json', RaceEntry.objects.all(), fields=('name', 'runner_number'), serializer=FixtureSerializer),
            serializers.serialize('json', RaceEntry.objects.all(), fields=('name', 'runner_number'))
        )

    def test_deserialize_fields(self):
        lhs = get_deserialized(RaceEntry.objects.all(), serializer=FixtureSerializer, fields=('runner_number',))
        rhs = get_deserialized(RaceEntry.objects.all(), fields=('runner_number',))
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_modelserializer_deserialize(self):
        lhs = get_deserialized(RaceEntry.objects.all(), serializer=RaceEntrySerializer)
        rhs = get_deserialized(RaceEntry.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize(self):
        lhs = get_deserialized(RaceEntry.objects.all(), serializer=FixtureSerializer)
        rhs = get_deserialized(RaceEntry.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize_xml(self):
        lhs = get_deserialized(RaceEntry.objects.all(), format='xml', serializer=FixtureSerializer)
        rhs = get_deserialized(RaceEntry.objects.all(), format='xml')
        self.assertTrue(deserialized_eq(lhs, rhs))

    # def test_xml_parsing(self):
    #     data = self.dumpdata.serialize('xml', RaceEntry.objects.all())
    #     object = list(self.dumpdata.deserialize('xml', data))[0].object
    #     print repr((object.name, object.runner_number, object.start_time, object.finish_time))


class TestNullPKModel(SerializationTestCase):
    def setUp(self):
        self.objs = [RaceEntry(
            name='John doe',
            runner_number=6014,
            start_time=datetime.datetime(year=2012, month=4, day=30, hour=9),
            finish_time=datetime.datetime(year=2012, month=4, day=30, hour=12, minute=25)
        )]

    def test_null_pk_dumpdata_json(self):
        self.assertEquals(
            serialize('json', self.objs, serializer=FixtureSerializer),
            serializers.serialize('json', self.objs)
        )

    def test_null_pk_dumpdata_yaml(self):
        self.assertEquals(
            serialize('yaml', self.objs, serializer=FixtureSerializer),
            serializers.serialize('yaml', self.objs)
        )

    def test_null_pk_dumpdata_xml(self):
        self.assertEquals(
            serialize('xml', self.objs, serializer=FixtureSerializer),
            serializers.serialize('xml', self.objs)
        )

    def test_modelserializer_deserialize(self):
        lhs = get_deserialized(self.objs, serializer=RaceEntrySerializer)
        rhs = get_deserialized(self.objs)
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize(self):
        lhs = get_deserialized(self.objs, serializer=FixtureSerializer)
        rhs = get_deserialized(self.objs)
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize_xml(self):
        lhs = get_deserialized(self.objs, format='xml', serializer=FixtureSerializer)
        rhs = get_deserialized(self.objs, format='xml')
        self.assertTrue(deserialized_eq(lhs, rhs))


##### Model Inheritance #####

class Account(models.Model):
    points = models.PositiveIntegerField()
    company = models.CharField(max_length=100)


class PremiumAccount(Account):
    date_upgraded = models.DateTimeField()


class PremiumAccountSerializer(ModelSerializer):
    class Meta:
        model = PremiumAccount


class TestModelInheritance(SerializationTestCase):
    def setUp(self):
        PremiumAccount.objects.create(
            points=42,
            company='Foozle Inc.',
            date_upgraded=datetime.datetime(year=2012, month=4, day=30, hour=9)
        )

    def test_dumpdata_child_model(self):
        self.assertEquals(
            serialize('json', PremiumAccount.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('json', PremiumAccount.objects.all())
        )

    def test_serialize_child_model(self):
        expected = [{
            'id': 1,
            'points': 42,
            'company': 'Foozle Inc.',
            'date_upgraded': datetime.datetime(2012, 4, 30, 9, 0)
        }]
        self.assertEquals(
            serialize('python', PremiumAccount.objects.all(), serializer=PremiumAccountSerializer),
            expected
        )

    def test_modelserializer_deserialize(self):
        lhs = get_deserialized(PremiumAccount.objects.all(), serializer=PremiumAccountSerializer)
        rhs = get_deserialized(PremiumAccount.objects.all())
        self.assertFalse(deserialized_eq(lhs, rhs))
        # We expect these *not* to match - the dumpdata implementation only
        # includes the base fields.

    def test_dumpdata_deserialize(self):
        lhs = get_deserialized(PremiumAccount.objects.all(), serializer=FixtureSerializer)
        rhs = get_deserialized(PremiumAccount.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))

    # TODO:
    # def test_dumpdata_deserialize_xml(self):
    #     lhs = get_deserialized(PremiumAccount.objects.all(), format='xml', serializer=FixtureSerializer)
    #     rhs = get_deserialized(PremiumAccount.objects.all(), format='xml')
    #     self.assertTrue(deserialized_eq(lhs, rhs))


# ##### Natural Keys #####

class PetOwnerManager(models.Manager):
    def get_by_natural_key(self, first_name, last_name):
        return self.get(first_name=first_name, last_name=last_name)


class PetManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)


class PetOwner(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birthdate = models.DateField()

    def natural_key(self):
        return (self.first_name, self.last_name)

    class Meta:
        unique_together = (('first_name', 'last_name'),)

    objects = PetOwnerManager()


class Pet(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(PetOwner, related_name='pets')

    def natural_key(self):
        return self.name

    objects = PetManager()


class TestNaturalKey(SerializationTestCase):
    """
    Test one-to-one field relationship on a model.
    """
    def setUp(self):
        joe = PetOwner.objects.create(
            first_name='joe',
            last_name='adams',
            birthdate=datetime.date(year=1965, month=8, day=27)
        )
        Pet.objects.create(
            owner=joe,
            name='splash gordon'
        )
        Pet.objects.create(
            owner=joe,
            name='frogger'
        )

    def test_naturalkey_dumpdata_json(self):
        """
        Ensure that we can replicate the existing dumpdata
        'use_natural_keys' behaviour.
        """
        self.assertEquals(
            serialize('json', Pet.objects.all(), use_natural_keys=True),
            serializers.serialize('json', Pet.objects.all(), use_natural_keys=True)
        )

    def test_naturalkey_dumpdata_yaml(self):
        """
        Ensure that we can replicate the existing dumpdata
        'use_natural_keys' behaviour.
        """
        self.assertEquals(
            serialize('yaml', Pet.objects.all(), use_natural_keys=True),
            serializers.serialize('yaml', Pet.objects.all(), use_natural_keys=True)
        )

    def test_naturalkey_dumpdata_xml(self):
        """
        Ensure that we can replicate the existing dumpdata
        'use_natural_keys' behaviour.
        """
        self.assertEquals(
            serialize('xml', Pet.objects.all(), use_natural_keys=True),
            serializers.serialize('xml', Pet.objects.all(), use_natural_keys=True)
        )

    def test_naturalkey(self):
        """
        Ensure that we can use NaturalKeyRelatedField to represent foreign
        key relationships.
        """
        class NaturalKeyModelSerializer(ModelSerializer):
            def get_related_field(self, model_field):
                return NaturalKeyRelatedField()

        expected = [{
            "owner": (u"joe", u"adams"),  # NK, not PK
            "id": 1,
            "name": u"splash gordon"
        }, {
            "owner": (u"joe", u"adams"),  # NK, not PK
            "id": 2,
            "name": u"frogger"
        }]
        self.assertEquals(
            serialize('python', Pet.objects.all(), serializer=NaturalKeyModelSerializer),
            expected
        )

    def test_naturalkey_reverse_relation(self):
        """
        Ensure that we can use NaturalKeyRelatedField to represent
        reverse foreign key relationships.
        """
        class PetOwnerSerializer(ModelSerializer):
            pets = NaturalKeyRelatedField()

        expected = [{
            "first_name": u"joe",
            "last_name": u"adams",
            "id": 1,
            "birthdate": datetime.date(1965, 8, 27),
            "pets": [u"splash gordon", u"frogger"]  # NK, not PK
        }]
        self.assertEquals(
            serialize('python', PetOwner.objects.all(), serializer=PetOwnerSerializer),
            expected
        )

    # def test_modelserializer_deserialize(self):
    #     lhs = get_deserialized(PetOwner.objects.all(), serializer=self.serializer)
    #     rhs = get_deserialized(PetOwner.objects.all())
    #     self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize(self):
        lhs = get_deserialized(Pet.objects.all(), serializer=FixtureSerializer, use_natural_keys=True)
        rhs = get_deserialized(Pet.objects.all(), use_natural_keys=True)
        self.assertTrue(deserialized_eq(lhs, rhs))


##### One to one relationships #####

class User(models.Model):
    email = models.EmailField()


class Profile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    country_of_birth = models.CharField(max_length=100)
    date_of_birth = models.DateTimeField()


class ProfileSerializer(ModelSerializer):
    class Meta:
        model = Profile


class NestedProfileSerializer(ModelSerializer):
    class Meta:
        model = Profile
        nested = True


class TestOneToOneModel(SerializationTestCase):
    """
    Test one-to-one field relationship on a model.
    """
    def setUp(self):
        user = User.objects.create(email='joe@example.com')
        Profile.objects.create(
            user=user,
            country_of_birth='UK',
            date_of_birth=datetime.datetime(day=5, month=4, year=1979)
        )

    def test_onetoone_dumpdata_json(self):
        self.assertEquals(
            serialize('json', Profile.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('json', Profile.objects.all())
        )

    def test_onetoone_dumpdata_yaml(self):
        self.assertEquals(
            serialize('yaml', Profile.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('yaml', Profile.objects.all())
        )

    def test_onetoone_dumpdata_xml(self):
        self.assertEquals(
            serialize('xml', Profile.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('xml', Profile.objects.all())
        )

    def test_onetoone_nested(self):
        expected = {
            'id': 1,
            'user': {
                'id': 1,
                'email': 'joe@example.com'
            },
            'country_of_birth': 'UK',
            'date_of_birth': datetime.datetime(day=5, month=4, year=1979)
        }
        self.assertEquals(
            serialize('python', Profile.objects.get(id=1), serializer=NestedProfileSerializer),
            expected
        )

    def test_onetoone_flat(self):
        expected = {
            'id': 1,
            'user': 1,
            'country_of_birth': 'UK',
            'date_of_birth': datetime.datetime(day=5, month=4, year=1979)
        }
        self.assertEquals(
            serialize('python', Profile.objects.get(id=1), serializer=ProfileSerializer),
            expected
        )

    def test_modelserializer_deserialize(self):
        lhs = get_deserialized(Profile.objects.all(), serializer=ProfileSerializer)
        rhs = get_deserialized(Profile.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize(self):
        lhs = get_deserialized(Profile.objects.all(), serializer=FixtureSerializer)
        rhs = get_deserialized(Profile.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))


class NestedUserSerializer(ModelSerializer):
    profile = ModelSerializer()


class FlatUserSerializer(ModelSerializer):
    profile = PrimaryKeyRelatedField()


class TestReverseOneToOneModel(SerializationTestCase):
    """
    Test reverse relationship of one-to-one fields.

    Note the Django's dumpdata serializer doesn't support reverse relations,
    which wouldn't make sense in that context, so we don't include them in
    the tests.
    """

    def setUp(self):
        user = User.objects.create(email='joe@example.com')
        Profile.objects.create(
            user=user,
            country_of_birth='UK',
            date_of_birth=datetime.datetime(day=5, month=4, year=1979)
        )

    def test_reverse_onetoone_nested(self):
        expected = {
            'id': 1,
            'email': u'joe@example.com',
            'profile': {
                'id': 1,
                'country_of_birth': u'UK',
                'date_of_birth': datetime.datetime(day=5, month=4, year=1979),
                'user': 1
            },
        }
        self.assertEquals(
            serialize('python', User.objects.get(id=1), serializer=NestedUserSerializer),
            expected
        )

    def test_reverse_onetoone_flat(self):
        expected = {
            'id': 1,
            'email': 'joe@example.com',
            'profile': 1,
        }
        self.assertEquals(
            serialize('python', User.objects.get(id=1), serializer=FlatUserSerializer),
            expected
        )


class Owner(models.Model):
    email = models.EmailField()


class Vehicle(models.Model):
    owner = models.ForeignKey(Owner, related_name='vehicles')
    licence = models.CharField(max_length=20)
    date_of_manufacture = models.DateField()


class VehicleSerializer(ModelSerializer):
    class Meta:
        model = Vehicle


class NestedVehicleSerializer(ModelSerializer):
    class Meta:
        model = Vehicle
        nested = True


class TestFKModel(SerializationTestCase):
    """
    Test one-to-one field relationship on a model.
    """
    def setUp(self):
        self.owner = Owner.objects.create(
            email='tom@example.com'
        )
        self.car = Vehicle.objects.create(
            owner=self.owner,
            licence='DJANGO42',
            date_of_manufacture=datetime.date(day=6, month=6, year=2005)
        )
        self.bike = Vehicle.objects.create(
            owner=self.owner,
            licence='',
            date_of_manufacture=datetime.date(day=8, month=8, year=1990)
        )

    def test_fk_dumpdata_json(self):
        self.assertEquals(
            serialize('json', Vehicle.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('json', Vehicle.objects.all())
        )

    def test_fk_dumpdata_yaml(self):
        self.assertEquals(
            serialize('yaml', Vehicle.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('yaml', Vehicle.objects.all())
        )

    def test_fk_dumpdata_xml(self):
        self.assertEquals(
            serialize('xml', Vehicle.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('xml', Vehicle.objects.all())
        )

    def test_fk_nested(self):
        expected = {
            'id': 1,
            'owner': {
                'id': 1,
                'email': u'tom@example.com'
            },
            'licence': u'DJANGO42',
            'date_of_manufacture': datetime.date(day=6, month=6, year=2005)
        }
        self.assertEquals(
            serialize('python', Vehicle.objects.get(id=1), serializer=NestedVehicleSerializer),
            expected
        )

    def test_fk_flat(self):
        expected = {
            'id': 1,
            'owner':  1,
            'licence': u'DJANGO42',
            'date_of_manufacture': datetime.date(day=6, month=6, year=2005)
        }
        self.assertEquals(
            serialize('python', Vehicle.objects.get(id=1), serializer=VehicleSerializer),
            expected
        )

    def test_modelserializer_deserialize(self):
        lhs = get_deserialized(Vehicle.objects.all(), serializer=VehicleSerializer)
        rhs = get_deserialized(Vehicle.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize(self):
        lhs = get_deserialized(Vehicle.objects.all(), serializer=FixtureSerializer)
        rhs = get_deserialized(Vehicle.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_reverse_fk_flat(self):
        class OwnerSerializer(ModelSerializer):
            vehicles = PrimaryKeyRelatedField()

        expected = {
            'id': 1,
            'email': u'tom@example.com',
            'vehicles':  [1, 2]
        }

        self.assertEquals(
            serialize('python', Owner.objects.get(id=1), serializer=OwnerSerializer),
            expected
        )

    def test_reverse_fk_nested(self):
        class NestedOwnerSerializer(ModelSerializer):
            vehicles = ModelSerializer()

        expected = {
            'id': 1,
            'email': u'tom@example.com',
            'vehicles': [
                {
                    'id': 1,
                    'licence': u'DJANGO42',
                    'owner': 1,
                    'date_of_manufacture': datetime.date(day=6, month=6, year=2005)
                }, {
                    'id': 2,
                    'licence': u'',
                    'owner': 1,
                    'date_of_manufacture': datetime.date(day=8, month=8, year=1990)
                }
            ]
        }
        self.assertEquals(
            serialize('python', Owner.objects.get(id=1), serializer=NestedOwnerSerializer),
            expected
        )


class Author(models.Model):
    name = models.CharField(max_length=100)


class Book(models.Model):
    authors = models.ManyToManyField(Author, related_name='books')
    title = models.CharField(max_length=100)
    in_stock = models.BooleanField()


class BookSerializer(ModelSerializer):
    class Meta:
        model = Book


class NestedBookSerializer(ModelSerializer):
    class Meta:
        model = Book
        nested = True


class TestManyToManyModel(SerializationTestCase):
    """
    Test one-to-one field relationship on a model.
    """
    def setUp(self):
        self.lucy = Author.objects.create(
            name='Lucy Black'
        )
        self.mark = Author.objects.create(
            name='Mark Green'
        )
        self.cookbook = Book.objects.create(
            title='Cooking with gas',
            in_stock=True
        )
        self.cookbook.authors = [self.lucy, self.mark]
        self.cookbook.save()

        self.otherbook = Book.objects.create(
            title='Chimera obscura',
            in_stock=False
        )
        self.otherbook.authors = [self.mark]
        self.otherbook.save()

    def test_m2m_dumpdata_json(self):
        self.assertEquals(
            serialize('json', Book.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('json', Book.objects.all())
        )
        self.assertEquals(
            serialize('json', Author.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('json', Author.objects.all())
        )

    def test_m2m_dumpdata_yaml(self):
        self.assertEquals(
            serialize('yaml', Book.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('yaml', Book.objects.all())
        )
        self.assertEquals(
            serialize('yaml', Author.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('yaml', Author.objects.all())
        )

    def test_m2m_dumpdata_xml(self):
        self.assertEquals(
            serialize('xml', Book.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('xml', Book.objects.all())
        )
        self.assertEquals(
            serialize('xml', Author.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('xml', Author.objects.all())
        )

    def test_m2m_nested(self):
        expected = {
            'id': 1,
            'title': u'Cooking with gas',
            'in_stock': True,
            'authors': [
                {'id': 1, 'name': 'Lucy Black'},
                {'id': 2, 'name': 'Mark Green'}
            ]
        }
        self.assertEquals(
            serialize('python', Book.objects.get(id=1), serializer=NestedBookSerializer),
            expected
        )

    def test_m2m_flat(self):
        expected = {
            'id': 1,
            'title': u'Cooking with gas',
            'in_stock': True,
            'authors': [1, 2]
        }
        self.assertEquals(
            serialize('python', Book.objects.get(id=1), serializer=BookSerializer),
            expected
        )

    def test_modelserializer_deserialize(self):
        lhs = get_deserialized(Book.objects.all(), serializer=BookSerializer)
        rhs = get_deserialized(Book.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))

    def test_dumpdata_deserialize(self):
        lhs = get_deserialized(Book.objects.all(), serializer=FixtureSerializer)
        rhs = get_deserialized(Book.objects.all())
        self.assertTrue(deserialized_eq(lhs, rhs))


class Anchor(models.Model):
    data = models.CharField(max_length=30)

    class Meta:
        ordering = ('id',)


class M2MIntermediateData(models.Model):
    data = models.ManyToManyField(Anchor, null=True, through='Intermediate')


class Intermediate(models.Model):
    left = models.ForeignKey(M2MIntermediateData)
    right = models.ForeignKey(Anchor)
    extra = models.CharField(max_length=30, blank=True, default="doesn't matter")


class TestManyToManyThroughModel(SerializationTestCase):
    """
    Test one-to-one field relationship on a model with a 'through' relationship.
    """
    def setUp(self):
        right = Anchor.objects.create(data='foobar')
        left = M2MIntermediateData.objects.create()
        Intermediate.objects.create(extra='wibble', left=left, right=right)
        self.obj = left

    def test_m2m_through_dumpdata_json(self):
        self.assertEquals(
            serialize('json', M2MIntermediateData.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('json', M2MIntermediateData.objects.all())
        )
        self.assertEquals(
            serialize('json', Anchor.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('json', Anchor.objects.all())
        )


class ComplexModel(models.Model):
    field1 = models.CharField(max_length=10)
    field2 = models.CharField(max_length=10)
    field3 = models.CharField(max_length=10)


class FieldsTest(SerializationTestCase):
    def test_fields(self):
        obj = ComplexModel(field1='first', field2='second', field3='third')

        # Serialize then deserialize the test database
        serialized_data = serialize('json', [obj], indent=2, fields=('field1', 'field3'), serializer=FixtureSerializer)
        result = next(deserialize('json', serialized_data, serializer=FixtureSerializer))

        # Check that the deserialized object contains data in only the serialized fields.
        self.assertEqual(result.object.field1, 'first')
        self.assertEqual(result.object.field2, '')
        self.assertEqual(result.object.field3, 'third')


class Actor(models.Model):
    name = models.CharField(max_length=20, primary_key=True)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name


class Movie(models.Model):
    actor = models.ForeignKey(Actor)
    title = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ('title',)

    def __unicode__(self):
        return self.title


class NonIntegerPKTests(SerializationTestCase):
    def test_unicode_fk(self):
        actor_name = u"Za\u017c\u00f3\u0142\u0107"
        movie_title = u'G\u0119\u015bl\u0105 ja\u017a\u0144'
        ac = Actor(name=actor_name)
        mv = Movie(title=movie_title, actor=ac)
        ac.save()
        mv.save()

        serial_str = serialize('json', [mv])
        self.assertEqual(serializers.serialize('json', [mv]), serial_str)

        obj_list = list(deserialize('json', serial_str))
        mv_obj = obj_list[0].object
        self.assertEqual(mv_obj.title, movie_title)

    def test_unicode_pk(self):
        actor_name = u"Za\u017c\u00f3\u0142\u0107"
        movie_title = u'G\u0119\u015bl\u0105 ja\u017a\u0144'
        ac = Actor(name=actor_name)
        mv = Movie(title=movie_title, actor=ac)
        ac.save()
        mv.save()

        serial_str = serialize('json', [ac], serializer=FixtureSerializer)
        self.assertEqual(serializers.serialize('json', [ac]), serial_str)

        obj_list = list(deserialize('json', serial_str, serializer=FixtureSerializer))
        ac_obj = obj_list[0].object
        self.assertEqual(ac_obj.name, actor_name)


class FileData(models.Model):
    data = models.FileField(null=True, upload_to='/foo/bar')


class FileFieldTests(SerializationTestCase):
    def test_serialize_file_field(self):
        FileData().save()
        self.assertEquals(
            serialize('json', FileData.objects.all(), serializer=FixtureSerializer),
            serializers.serialize('json', FileData.objects.all())
        )


class Category(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name


class ArticleAuthor(models.Model):
    name = models.CharField(max_length=20)

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return self.name


class Article(models.Model):
    author = models.ForeignKey(ArticleAuthor)
    headline = models.CharField(max_length=50)
    pub_date = models.DateTimeField()
    categories = models.ManyToManyField(Category)

    class Meta:
        ordering = ('pub_date', )

    def __unicode__(self):
        return self.headline


class TestRoundtrips(SerializationTestCase):
    def setUp(self):
        sports = Category.objects.create(name="Sports")
        music = Category.objects.create(name="Music")
        op_ed = Category.objects.create(name="Op-Ed")

        self.joe = ArticleAuthor.objects.create(name="Joe")
        self.jane = ArticleAuthor.objects.create(name="Jane")

        self.a1 = Article(
            author=self.jane,
            headline="Poker has no place on ESPN",
            pub_date=datetime.datetime(2006, 6, 16, 11, 00)
        )
        self.a1.save()
        self.a1.categories = [sports, op_ed]

        self.a2 = Article(
            author=self.joe,
            headline="Time to reform copyright",
            pub_date=datetime.datetime(2006, 6, 16, 13, 00, 11, 345)
        )
        self.a2.save()
        self.a2.categories = [music, op_ed]

    def test_serializer_roundtrip(self):
        """Tests that serialized content can be deserialized."""
        serial_str = serialize('xml', Article.objects.all(), serializer=FixtureSerializer)
        models = list(deserialize('xml', serial_str, serializer=FixtureSerializer))
        self.assertEqual(len(models), 2)

    def test_altering_serialized_output(self):
        """
        Tests the ability to create new objects by
        modifying serialized content.
        """
        old_headline = "Poker has no place on ESPN"
        new_headline = "Poker has no place on television"
        serial_str = serialize('xml', Article.objects.all(), serializer=FixtureSerializer)

        serial_str = serial_str.replace(old_headline, new_headline)
        models = list(deserialize('xml', serial_str, serializer=FixtureSerializer))

        # Prior to saving, old headline is in place
        self.assertTrue(Article.objects.filter(headline=old_headline))
        self.assertFalse(Article.objects.filter(headline=new_headline))

        for model in models:
            model.save()

        # After saving, new headline is in place
        self.assertTrue(Article.objects.filter(headline=new_headline))
        self.assertFalse(Article.objects.filter(headline=old_headline))
