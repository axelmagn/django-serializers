# Django Serializers

**Customizable Serialization for Django.**

**Author:** Tom Christie, [Follow me on Twitter][1].

---

**Note**: This project has now been superseded by the serializer implementation in `django-rest-framework` (which originated from this project).
You should instead install and use [django-rest-framework].

Note that the serializers in REST framework are decoupled from other aspects of the codebase, so you won't have any problems using them even if you're not actually building a Web API.

---

## Overview

`django-serializers` gives you a declarative serialization and deserialization API, that mirrors Django's `Form`/`ModelForm` API.  It provides flexible serialization and deserialization of objects, models and querysets, and is intended to be a potential replacement for Django's current  fixture serialization.

Features:

* Arbitrary objects can be serialized using the `Serializer` class.
* Models and querysets can be serialized using the `ModelSerializer` class.
* Supports backwards compatible fixture serialization, using the `FixtureSerializer` class.
* Supports flat or nested serialization, and handles depth and recursive relationships.
* Supports `json`, `yaml`, `xml` and `csv` formats out of the box.
* Relationships can be serialized to primary keys, natural keys, or custom implementations.
* Includes a comprehensive test suite and passes Django's existing serialization tests.

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

You can also run `django-serializers` against the existing Django serialization tests:

    manage.py testcompat

# Working with Serializers

## Serializing objects

Let's start by creating a simple object we can use for example purposes:

```python
    class Comment(object):
        def __init__(self, title, content, created=None):
            self.title = title
            self.content = content
            self.created = created or datetime.datetime.now()
    
    comment = Comment(title='blah', content='foo bar baz')
```

We'll declare a serializer that we can use to serialize and deserialize `Comment` objects.
Declaring a serializer looks very similar to declaring a form:

```python
    class CommentSerializer(Serializer):
        title = CharField()
        content = CharField()
        created = DateTimeField(label='created time')
```

We can now use `CommentSerializer` to serialize a comment, or list of comments, into `json`, `yaml`, `xml` or `csv` formats:

```python
    >>> serializer = CommentSerializer()
    >>> stream = serializer.serialize('json', comment, indent=4)
    >>> print stream
    {
        "title": "blah", 
        "content": "foo bar baz", 
        "created time": "2012-07-12T09:01:14.302"
    }
```

## Deserializing objects

We can deserialize encoded data, using the same serializer class: 

```python
    >>> serializer.deserialize('json', stream)
    {'content': u'foo bar baz', 'created': datetime.datetime(2012, 7, 12, 9, 1, 14, 302000), 'title': u'blah'}
```

Note that when we deserialized the stream, we ended up with a dictionary containing the correct fields, but we haven't got a fully deserialized `Comment` instance.  

That's because the `CommentSerializer` doesn't yet have any way of determining what class it should deserialize objects into, or how those objects should be instantiated.

We can explicitly control how the deserialized objects are instantiated by defining the `revert_object` method:

```python
    class CommentSerializer(Serializer):
        title = CharField()
        content = CharField()
        created = DateTimeField(label='created time')
       
        def revert_object(self, attrs, instance=None):
            return Comment(**attrs)
```

Declaring the `revert_object` method is optional, and may not be required if you don't need to support deserialization.

## Validation

Deserializing the data also applies validation, in much the same way as occurs when using Forms.
If validation fails, a `ValidationError` will be raised.

**TODO: Describe validation in more depth**

## Dealing with nested objects

The previous example is fine for dealing with objects that only have simple datatypes, but sometimes we also need to be able to represent more complex objects,
where some of the attributes of an object might not be simple datatypes such as strings, dates or integers.

The `Serializer` class is itself a type of `Field`, and can be used to represent relationships where one object type is nested inside another.

```python
    class UserSerializer(Serializer):
        email = EmailField()
        username = CharField()
        
        def revert_object(cls, attrs):
            return User(**attrs)


    class CommentSerializer(Serializer):
        user = UserSerializer()
        title = CharField()
        content = CharField()
        created = DateTimeField(label='created time')
        
        def revert_object(self, attrs):
            return Comment(**attrs)
```

## Creating custom fields

If you want to create a custom field, you'll probably want to override either one or both of the `.to_native()` and `.from_native()` methods.  These two methods are used to convert between the intial datatype, and a primative, serializable datatype.  Primative datatypes may be any of a number, string, date/time/datetime or None.  They may also be any list or dictionary like object that only contains other primative objects.

The `.to_native()` method is called to convert the initial datatype into a primative, serializable datatype.  The `from_native()` method is called to restore a primative datatype into it's initial representation.

Let's look at an example of serializing a class that represents an RGB color value:

```python
    class Color(object):
        """
        A color represented in the RGB colorspace.
        """

        def __init__(self, red, green, blue):
            assert(red >= 0 and green >= 0 and blue >= 0)
            assert(red < 256 and green < 256 and blue < 256)
            self.red, self.green, self.blue = red, green, blue

    class ColourField(Field):
        """
        Color objects are serialized into "rgb(#, #, #)" notation.
        """

        def to_native(self, obj):
            return "rgb(%d, %d, %d)" % (obj.red, obj.green, obj.blue)
      
        def from_native(self, data):
            data = data.strip('rgb(').rstrip(')')
            red, green, blue = [int(col) for col in data.split(',')]
            return Color(red, green, blue)
```

By default field values are treated as mapping to an attribute on the object.  If you need to customize how the field value is accessed and set you need to override `.field_to_native()` and/or `.field_from_native()`.

As an example, let's create a field that can be used represent the class name of the object being serialized:

```python
    class ClassNameField(Field):
        def field_to_native(self, obj, field_name):
            """
            Serialize the object's class name, not an attribute of the object.
            """
            return obj.__class__.__name__

        def field_from_native(self, data, field_name, into):
            """
            We don't want to set anything when we revert this field.
            """
            pass
```

---

# Working with ModelSerializers

Often you'll want serializer classes that map closely to model definitions.
The `ModelSerializer` class lets you automatically create a Serializer class with fields that corrospond to the Model fields.

```python
    class AccountSerializer(ModelSerializer):
        class Meta:
            model = Account
```

**[TODO: Explain model field to serializer field mapping in more detail]**

## Specifying fields explicitly 

You can add extra fields to a `ModelSerializer` or override the default fields by declaring fields on the class, just as you would for a `Serializer` class.

```python
    class AccountSerializer(ModelSerializer):
        url = CharField(source='get_absolute_url', readonly=True)
        group = NaturalKeyField()

        class Meta:
            model = Account
```

Extra fields can corrospond to any property or callable on the model.

## Relational fields

When serializing model instances, there are a number of different ways you might choose to represent relationships.  The default representation is to use the primary keys of the related instances.

Alternative representations include serializing using natural keys, serializing complete nested representations, or serializing using a custom representation, such as a URL that uniquely identifies the model instances.

The `PrimaryKeyField` and `NaturalKeyField` fields provide alternative flat representations.

The `ModelSerializer` class can itself be used as a field, in order to serialize relationships using nested representations.

The `RelatedField` class may be subclassed to create a custom represenation of a relationship.  The subclass should override `.to_native()`, and optionally `.from_native()` if deserialization is supported.

All the relational fields may be used for any relationship or reverse relationship on a model.

## Specifying which fields should be included

If you only want a subset of the default fields to be used in a model serializer, you can do so using `fields` or `exclude` options, just as you would with a `ModelForm`.

For example:

```python
    class AccountSerializer(ModelSerializer):
        class Meta:
            model = Account
            exclude = ('id',)
```

The `fields` and `exclude` options may also be set by passing them to the `serialize()` method.

**[TODO: Possibly only allow .serialize(fields=…) in FixtureSerializer for backwards compatability, but remove for ModelSerializer]**

## Specifiying nested serialization

The default `ModelSerializer` uses primary keys for relationships, but you can also easily generate nested representations using the `nested` option:

```python
    class AccountSerializer(ModelSerializer):
        class Meta:
            model = Account
            exclude = ('id',)
            nested = True
```


The `nested` option may be set to either `True`, `False`, or an integer value.  If given an integer value it indicates the depth of relationships that should be traversed before reverting to a flat representation.

When serializing objects using a nested representation any occurances of recursion will be recognised, and will fall back to using a flat representation.

The `nested` option may also be set by passing it to the `serialize()` method.

**[TODO: Possibly only allow .serialize(nested=…) in FixtureSerializer]**

## Customising the default fields used by a ModelSerializer

```python
    class AccountSerializer(ModelSerializer):
        class Meta:
            model = Account

        def get_nested_field(self, model_field):
            return ModelSerializer()

        def get_related_field(self, model_field):
            return NaturalKeyField()

        def get_field(self, model_field):
            return Field()
```

---

# Customizing encoding formats

Out of the box `django-serializers` supports `json`, `yaml`, `xml` and `csv` formats.  You can support other formats, or modify the existing formats, by writing custom renderer and parser classes.

## Renderers

* Explain that input is native python datatypes.
* Same as output of `.serialize('python', objects)`
* Give HTML table example

## Parsers


## Providing additional metadata

* Sometimes need to be able to get at the Field instance used for each field.
* format-specific metadata.
* XML `attributes`, other examples: For HTML Field might have `template` or `widget`.

---

# Creating custom Serializer types

Describe how to write totally custom serializer classes, that determine their fields automatically based on the object being serialized, or the data being deserialized.

Give an example, using an `ObjectSerializer` class, that serializes all the instance attributes on an object. 

* `.default_fields(self, serialize, obj=None, data=None, nested=False)`

---

# API Reference

## Basic field types

The base class for basic field types is `Field`.

Classes:

* `BooleanField`
* `CharField`
* `DateField`
* `DateTimeField`
* `IntegerField`
* `FloatField`

Methods:

* `.__init__(self, label=None, source=None, readonly=False)`
* `.initialize(self, parent, model_field)`
* `.to_native(self, value)`
* `.from_native(self, value)`
* `.field_to_native(self, obj, attr)`
* `.field_from_native(self, data, field_name, into)`
* `.attributes(self)`

Attributes:

* `.root`
* `.parent`
* `.context`
* `.model_field`

**TODO: Factor `model_field` out of initialize.**

**TODO: Field options: `errors`, `blank`, etc…**

## Relational field types

The base class for relational field types is `RelatedField`.

Classes:

* `PrimaryKeyField`
* `NaturalKeyField`

## Serializers

Classes:

* `Serializer`
* `ModelSerializer`
* `FixtureSerializer`

Methods:

* `.__init__(self, context=None)`
* `.serialize(self, format, object, context=None, fields=None, exclude=None, nested=None, **options)`
* `.deserialize(self, format, stream, **options)`
* `.render(self, data, stream, format, **options)`
* `.parse(self, stream, format, **options)`
* `.to_native(self, obj)`
* `.from_native(self, data)`
* `.default_fields(self, obj, data, nested)`
* `.field_key(self, field_name)`
* `.convert_object(self, obj)`
* `.restore_fields(self, data)`
* `.restore_object(self, attrs)`

Attributes:

* `.opts`
* `.fields`

## Parsers & Renderers

The base classes are `Parser` and `Renderer`.

* `XMLParser`/`XMLRenderer`
* `YAMLParser`/`YAMLRenderer`
* `JSONParser`/`JSONRenderer`
* `CSVParser`/`CSVRenderer`

Methods:

* `.render(self, data, **options)`
* `.parse(self, stream)`

---

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
[2]: http://github.com/tomchristie/django-auto-api
[django-rest-framework]: https://github.com/tomchristie/django-rest-framework/
