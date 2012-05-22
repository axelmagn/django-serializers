# Django Serializers

**Customizable Serialization for Django.**

**Author:** Tom Christie, [Follow me on Twitter][1].

## Overview

django-serializers provides flexible serialization of objects, models and
querysets.

It is intended to be a potential replacement for the current, inflexible
serialization.  It should be able to support the current `dumpdata` format,
whilst also being easy to override and customise.

Serializers are declared in a simlar format to `Form` and `Model` declarations,
with an inner `Meta` class providing general options, and optionally with a set
of `Field` and/or `Serializer` classes being declaring inside the parent `Serializer` class.

Features:

* Supports serialization of arbitrary python objects using the `ObjectSerializer` class.
* Supports serialization of models and querysets using `ModelSerializer`.
* Supports serialization to the existing dumpdata format, using `DumpDataSerializer`.
* Supports flat serialization, and nested serialization (to arbitrary depth), and handles recursive relationships.
* Allows for both implicit fields, which are determined at the point of serialization, and explicit fields, which are declared on the serializer class.
* The declaration of the serialization structure is handled independantly of the final encoding used (eg 'json', 'xml' etc…).  This is desirable for eg. APIs which want to support a given dataset being output to a number of different formats.
* Currently supports 'json', 'yaml', 'xml', 'csv', 'html'.
* Supports both fields that corrospond to Django model fields, and fields that corrospond to other attributes, such as `get_absolute_url`.
* Supports relations serializing to primary keys, natural keys, or custom implementations.
* Supports streaming output, rather than loading all objects into memory.
* Hooks throughout to allow for complete customization.  Eg. Writing key names using javascript style camel casing.
* Simple, clean API.
* Comprehensive test suite.
* Backwards compatible with the existing `dumpdata` serialization API.
* Passes Django's existing serialization test suite.

Notes:

* `django-serializers` currently does not address deserialization.  Replacing
the existing `loaddata` deserialization with a more flexible deserialization
API is considered out of scope until the serialization API has first been adequatly addressed.

For an example of using `django-serializers` to create Web APIs,
please see [django-auto-api][2].

# Requirements

Currently requires Django >= 1.4

# Installation

Install using pip:

    pip install django-serializers

Optionally, if you want to include the `django-serializer` tests in your
project, add `serializers` to your `INSTALLED_APPS` setting:

    INSTALLED_APPS = (
        ...
        'serializers',
    )

Note that if you have cloned the git repo you can run the tests directly, with
the provided `manage.py` file:

    manage.py test

# Examples

We'll use the following example class to show some simple examples
of serialization:

    class Person(object):
        def __init__(self, first_name, last_name, age):
            self.first_name = first_name
            self.last_name = last_name
            self.age = age

        @property
        def full_name(self):
            return self.first_name + ' ' + self.last_name

You can serialize arbitrary objects using the `Serializer` class.  Objects are
serialized into dictionaries, containing key value pairs of any non-private
instance attributes on the object:

    >>> from serializers import Serializer
    >>> person = Person('john', 'doe', 42)
    >>> serializer = Serializer()
    >>> print serializer.encode(person, 'json', indent=4)
    {
        'first_name': 'john',
        'last_name': 'doe',
        'age': 42
    }

Let's say we only want to include some specific fields.  We can do so either by
setting those fields when we instantiate the `Serializer`...

    >>> serializer = Serializer(fields=('first_name', 'age'))
    >>> print serializer.encode(person, 'json', indent=4)
    {
        'first_name': 'john',
        'age': 42
    }

...Or by defining a custom `Serializer` class:

    >>> class PersonSerializer(Serializer):
    >>>     class Meta:
    >>>         fields = ('first_name', 'age')
    >>>
    >>> print PersonSerializer().encode(person, 'json', indent=4)
    {
        'first_name': 'john',
        'age': 42
    }

We can also include additional attributes on the object to be serialized, or
exclude existing attributes:

    >>> class PersonSerializer(Serializer):
    >>>     class Meta:
    >>>         exclude = ('first_name', 'last_name')
    >>>         include = 'full_name'
    >>>
    >>> print PersonSerializer().encode(person, 'json', indent=4)
    {
        'full_name': 'john doe',
        'age': 42
    }

To explicitly define how the object fields should be serialized, we declare
those fields on the serializer class:

    >>> class PersonSerializer(Serializer):
    >>>    first_name = Field(label='First name')
    >>>    last_name = Field(label='Last name')
    >>>
    >>> print PersonSerializer().encode(person, 'json', indent=4)
    {
        'First name': 'john',
        'Last name': 'doe'
    }

We can also define new types of field and control how they are serialized:

    >>> class ClassNameField(Field):
    >>>     def serialize(self, obj)
    >>>         return obj.__class__.__name__
    >>>
    >>>     def get_field_value(self, obj, field_name):
    >>>         return obj
    >>>
    >>> class ObjectSerializer(Serializer):
    >>>     class_name = ClassNameField(label='class')
    >>>     fields = Serializer(source='*')
    >>>
    >>> print ObjectSerializer().encode(person, 'json', indent=4)
    {
        'class': 'Person',
        'fields': {
            'first_name': 'john',
            'last_name': 'doe',
            'age': 42
        }
    }

django-serializers also handles nested serialization of objects:

    >>> fred = Person('fred', 'bloggs', 41)
    >>> emily = Person('emily', 'doe', 37)
    >>> jane = Person('jane', 'doe', 44, partner=fred)
    >>> john = Person('john', 'doe', 42, siblings=[jane, emily])
    >>> Serializer().serialize(john)
    {
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

And handles flat serialization of objects:

    >>> Serializer(depth=0).serialize(john)
    {
        'first_name': 'john',
        'last_name': 'doe',
        'age': 42,
        'siblings': [
            'jane doe',
            'emily doe'
        ]
    }

Similarly model and queryset serialization is supported, and handles either
flat or nested serialization of foreign keys, many to many relationships, and
one to one relationships, plus reverse relationships:

    >>> class User(models.Model):
    >>>     email = models.EmailField()
    >>>
    >>> class Profile(models.Model):
    >>>     user = models.OneToOneField(User, related_name='profile')
    >>>     country_of_birth = models.CharField(max_length=100)
    >>>     date_of_birth = models.DateTimeField()
    >>>
    >>> ModelSerializer().serialize(profile)
    {
        'id': 1,
        'user': {
            'id': 1,
            'email': 'joe@example.com'
        },
        'country_of_birth': 'UK',
        'date_of_birth': datetime.datetime(day=5, month=4, year=1979)
    }

**TODO:**  Needs more ModelSerializer examples.


# Field reference

## Field options

The following options may be provided when instatiating a `Field`.

### label

If `label` is set it determines the name that should be used as the
key when serializing the field.

### source

If `source` is set it determines which attribute of the object to
retrieve when serializing the field.

A value of '*' is a special case, which denotes the entire object should be
passed through and serialized by this field.

For example, the following serializer:

    class ClassNameField(Field):
        def serialize(self, obj):
            return obj.__class__.__name__

        def get_field_value(self, obj, field_name):
            return obj

    class CustomSerializer(Serializer):
        class_name = ClassNameField(label='class')
        fields = Serializer(source='*', depth=0)

Would serialize objects into a structure like this:

    {
        "class": "Person"
        "fields": {
            "age": 23, 
            "name": "Frank"
            ...
        }, 
    }

### convert

Provides a simple way to override the default convert function.
`convert` should be a function that takes a single argument and returns
the converted output.

For example:

    class CustomSerializer(Serializer):
        email = Field(convert=lamda obj: obj.lower())  # Force email fields to lowercase.
        ...

## Field methods

### convert(self, obj)

Returns a native python datatype representing the given object.

If you are writing a custom field, overiding `convert()` will let
you customise how the output is generated.

### convert_field(self, obj, field_name)

Returns a native python datatype representing the given `field_name`
attribute on `object`.

This defaults to getting the attribute from `obj` using `getattr`, and
calling `convert` on the result.

If you are writing a custom `Field`and need to control exactly which attributes
of the object are serialized, you will need to override this method instead of
the `convert` method.

(For example if you are writing a`datetime` serializer which combines
information from two seperate `date` and `time` attributes on an object, or
perhaps if you are writing a `Field` serializer which serializes some
non-attribute aspect of the object such as it's class name)

### attributes(self)

`attributes()` should return a dictionary that may be used when rendering to xml
to determine the attribtues on the tag that represents this field.
The default implementation returns an empty dictionary.


## Available fields

### Field

The base class.  Converts objects into primative types, descending into
dictionaries and lists as needed, and using string representations of objects
that do not have a primative representation.

### ModelField

The base class for model fields.  Returns the field value as a primative type.

### RelatedField

The base class for relational model fields.  You should not use this class
directly, but you may subclass it and override `convert()` in order to create a
custom relational field.

### PrimaryKeyRelatedField

Returns related instances as their primrary key representations.

### NaturalKeyRelatedField

Returns related instances as their natural key representations.


# Serializer reference

## Serializer options

Serializer options may be specified in the class definition, on the `Meta`
inner class, or set when instatiating the `Serializer` object.

For example, using the `Meta` inner class:

    class PersonSerializer(ModelSerializer):
        class Meta:
            fields = ('full_name', 'age')

    serializer = PersonSerializer()

And the same, using arguments when instantiating the serializer.

    serializer = ModelSerializer(fields=('full_name', 'age'))

The serializer class is a subclass of `Field`, so also supports the `Field` API.

### include

A list of field names that should be included in the output.  This could
include properties, class attributes, or any other attribute on the object that
would not otherwise be serialized.

### exclude

A list of field names that should not be included in the output.

### fields

The complete list of field names that should be serialized.  If provided
`fields` will override `include` and `exclude`.

### depth

The `depth` argument controls how nested objects should be serialized.
The default is `None`, which means serialization should descend into nested
objects.

If `depth` is set to an integer value, serialization will descend that many
levels into nested objects, before starting serialize nested models with a
"flat" value.

For example, setting `depth=0` ensures that only the fields of the top level
object will be serialized, and any nested objects will simply be serialized
as simple string representations of those objects.

### include_default_fields

By default any default fields on an object will be serialized, along with
any explicity declared fields.

If `include_default_fields` is set to `False`, then *only* the explicitly
specified serializer fields will be used.

For example, in this case, both the 'full_name' field, and any instance
attributes on the object will be serialized:

    class CustomSerializer(Serializer):
        full_name = Serializer(label='Full name')

In this case, only the 'full_name' field will be serialized:

    class CustomSerializer(Serializer):
        full_name = Serializer(label='Full name')

        class Meta:
            include_default_fields = False

### format

If specified, format gives the default format that should be used by the
`serialize` function.  Options are `json`, `yaml`, `xml`, `csv`, `html`.

Specifying a `format` allows the serializer to be backwards compatible with
Django's existing serializers.  (So for instance, you can use it with the
`SERIALIZATION_MODULES` setting.)

Serializer methods
==================

### serialize(self, obj, format=None, **opts)

The main entry point into serializers.

`format` should be a string representing the desired encoding.  Valid choices
are `json`, `yaml`, `xml`, `csv` and `html`.
If format is left as `None`, and no default format for the serializer is given
by the `format` option, then the object will be serialized into a python object
in the desired structure, but will not be rendered into a final output format.

`opts` may be any additional options specific to the encoding.

Internally serialization is a two-step process.  The first step calls the
`convert()` method, which serializes the object into the desired structure,
limited to a set of primative python datatypes.  The second step calls the
`render()` method, which renders that structure into the final output string
or bytestream.

### convert(self, obj)

Converts the given object or container into a primative representation which
can be directly rendered.

The default implementation will descend into dictionary and iterable
containers, and call `convert_object` on any objects found inside those.

You won't typically need to override this, unless you want to heavily customise
how objects are serialized, (For example if you want to wrap your serialization
output in some container data) or want to write a custom `Serializer`.
(For example if you're writing a  serializer which takes dictionary-like
objects, and uses the keys as fields.)

### convert_object(self, obj)

Converts the given object into a primative representation which can be directly rendered.
This method is called by `convert()` for each object it finds that needs serializing.
You won't typically need to override this method, but you will want to call
into it, if you're overriding `convert`.

### render(self, data, stream, format, **opts)

Render the primative representation `data` into a bytestream.
You won't typically need to override this method.

### get_field_key(self, obj, field_name, field)

Returns a native python object representing the key for the given field name.
By default this will be the serializer's `label` if it has one specified,
or the `field_name` string otherwise.

Override this to provide custom behaviour, for example to represent keys using
javascipt style upperCasedNames.

### get_default_field_names(self, obj)

Return the default set of field names that should be serialized for an object.
If a serializer has no `Serializer` classes declared as fields, then this will
be the set of fields names that will be serialized.

### get_flat_serializer(self, obj, field_name)

Return a default field instance for the given field, if the maximum depth has
been reached, or recursion has occurred.

### get_nested_serializer(self, obj, field_name)

Return a default field instance for the given field, if the maximum depth has
not yet been reached and recursion has not occurred.

# Available serializers


## Serializer

The `Serializer` class may not be used directly, but may be overridden if you
want to write a custom serializer.

## ObjectSerializer

`ObjectSerializer` may be used to serialize arbitrary python objects.
The default set of fields will be all the non-private instance attributes on
each object.

`ObjectSerializer` supports all the options for Serializer, as well as
these additional options.

### flat_field

The class that should be used for serializing flat fields.  (ie. Once the
specified `depth` has been reached.)  Default is `Field`.

### nested_field

The class that should be used for serializing nested fields.  (ie Before the
specified `depth` has been reached.)  Default is `None`, which indicates that
the serializer should use another instance of it's own class.

## ModelSerializer

`ModelSerializer` may be used to serialize Django model instances and querysets.
The default set of fields will be all the model fields on each instance.

`ModelSerializer` supports all the options for Serializer, as well as
these additional options.

### model_field

The default field class that should be used for serializing non-related model
fields.

The default is `ModelField`.

### non_model_field

The default field class that should be used for serializing attributes on the
model instance that are not model fields.  (For instance `get_absolute_url`.)

The default is `Field`.

### related_field

The default field class that should be used for serializing related model
fields once the maximum depth has been reached, or recursion occurs.

`related_field` can be applied to `OneToOneField`, `ForeignKey`,
`ManyToManyField`, or any of their corrosponding reverse managers.

The default is `PrimaryKeyRelatedField`.

### nested_related_field

The default field class that should be used for serializing related model
fields before the maximum depth has been reached, or recursion occurs.

The default is `None`, which indicates that the serializer's own class should
be reused for nested relations.

### model_field_types

A list of model field types that should be serialized by default.
Available options are: 'pk', 'fields', 'many_to_many', 'local_fields',
'local_many_to_many'.

The default value is ('pk', 'fields', 'many_to_many').

Note that the DumpDataSerializer uses a slightly different set of fields, in
order to correctly deal with it's particular requirements.

## DumpDataSerializer

`DumpDataSerializer` may be used to serialize Django model instances and
querysets into the existing `dumpdata` format.



# Changelog

### 0.5.0

* Backwards compatible with existing serialization and passing Django's
serializer tests.

### 0.4.0

* Dumpdata support for json and yaml.  xml nearly complete.

### 0.3.2

* Fix csv for python 2.6

### 0.3.1

* Fix import error when yaml not installed

### 0.3.0

* Initial support for CSV.

### 0.2.0

* First proper release. Properly working model relationships etc…

### 0.1.0

* Initial release

# Possible extras…

* Tests for non-numeric FKs, and FKs with a custom db implementation.
* Tests for many2many FKs with a 'through' model.
* Tests for proxy models.
* Finish off xml dumpdata backward compat - many to many, natural keys, None & None on datetime fields all need tweaking.
* Default xml renderer needs to include attributes, not just the dumpdata one.
* JSON renderer needs a little tweaking to properly support streaming, rather than loading all items into memory.
* `fields` option in serialize currently only supported by dumpdata serializer.  How to deal with this?  Should source='*' should have the effect of passing through `fields`, `include`, `exclude` to the child field, instead of applying to the parent serializer, so eg. DumpDataSerializer will recognise that those arguments apply to the `fields:` level, rather than referring to what should be included at the root level.
* Consider character encoding issues.
* `stack` needs to be reverted at start of new serialization.
* Performance testing.
* Indent option for xml.
* I'd like to add `nested.field` syntax to the `include`, `exclude` and `field` argument, to allow quick declarations of nested representations.
* Add `nested.field` syntax to the `source` argument, to allow quick declarations of serializing nested elements into a flat output structure.
* Better `csv` format.  (Eg nested fields)

# License

Copyright © Tom Christie.

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.
Redistributions in binary form must reproduce the above copyright notice, this
list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

[1]: http://twitter.com/_tomchristie
[2]: https://github.com/tomchristie/django-auto-api
