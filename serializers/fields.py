import datetime
from django.utils.encoding import is_protected_type, smart_unicode
from django.core import validators
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models.related import RelatedObject
from django.db import models
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.translation import ugettext_lazy as _
from serializers.utils import is_simple_callable
import warnings


class Field(object):
    creation_counter = 0

    def __init__(self, label=None, convert=None):
        self.label = label
        if convert:
            self.convert = convert
        self.parent = None
        self.creation_counter = Field.creation_counter
        Field.creation_counter += 1

    def _convert_field(self, obj, field_name, parent):
        """
        The entry point into a field, as called by it's parent serializer.
        """
        self.obj = obj
        self.field_name = field_name
        self.parent = parent
        self.root = parent.root or parent
        return self.convert_field(obj, field_name)

    def _revert_field(self, data, field_name, into, parent):
        self.parent = parent
        self.revert_field(data, field_name, into)

    def revert_field(self, data, field_name, into):
        into[field_name] = self.revert(data.get(field_name))

    def convert_field(self, obj, field_name):
        """
        Given the parent object and the field name, returns the field value
        that should be serialized.
        """
        return self.convert(getattr(obj, field_name))

    def convert(self, obj):
        """
        Converts the field's value into it's simple representation.
        """
        if is_protected_type(obj):
            return obj
        elif is_simple_callable(obj):
            return self.convert(obj())
        elif isinstance(obj, dict):
            return dict([(key, self.convert(val))
                         for (key, val) in obj.items()])
        elif hasattr(obj, '__iter__'):
            return [self.convert(item) for item in obj]
        return smart_unicode(obj)

    def attributes(self):
        return {}


class ModelField(Field):
    def convert_field(self, obj, field_name):
        try:
            self.field = obj._meta.get_field_by_name(self.field_name)[0]
        except:
            pass
        return super(ModelField, self).convert_field(obj, field_name)

    # def revert_field(self, data, field_name, into):
    #     into[field_name] = self.revert(data.get(field_name))

    def attributes(self):
        return {
            "type": self.field.get_internal_type()
        }


class RelatedField(ModelField):
    """
    A base class for model related fields or related managers.

    Subclass this and override `convert` to define custom behaviour when
    serializing related objects.
    """

    def convert_field(self, obj, field_name):
        obj = getattr(obj, field_name)
        if obj.__class__.__name__ in ('RelatedManager', 'ManyRelatedManager'):
            return [self.convert(item) for item in obj.all()]
        return self.convert(obj)

    def attributes(self):
        field = self.obj._meta.get_field_by_name(self.field_name)[0]
        return {
            "rel": field.rel.__class__.__name__,
            "to": smart_unicode(field.rel.to._meta)
        }


class PrimaryKeyRelatedField(RelatedField):
    """
    Serializes a model related field or related manager to a pk value.
    """

    # Note the we use ModelRelatedField's implementation, as we want to get the
    # raw database value directly, since that won't involve another
    # database lookup.
    #
    # An alternative implementation would simply be this...
    #
    # class PrimaryKeyRelatedField(RelatedField):
    #     def convert(self, obj):
    #         return obj.pk

    error_messages = {
        'invalid': _(u"'%s' value must be an integer."),
    }

    def convert(self, pk):
        """
        Simply returns the object's pk.  You can subclass this method to
        provide different serialization behavior of the pk.
        (For example returning a URL based on the model's pk.)
        """
        return pk

    def revert(self, value):
        # self.field = self.obj._meta.get_field_by_name(self.field_name)[0]
        # print self.field.rel.to._meta.get_field(self.field.rel.field_name).to_python(value)

        # # Bit of a hack to deal with many-related
        # if hasattr(value, '__iter__'):
        #     return [self.revert(item) for item in value]

        if value in validators.EMPTY_VALUES:
            return None
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(self.error_messages['invalid'])
        return value

    def convert_field(self, obj, field_name):
        self.test = field_name
        try:
            obj = obj.serializable_value(field_name)
        except AttributeError:
            field = obj._meta.get_field_by_name(field_name)[0]
            obj = getattr(obj, field_name)
            if obj.__class__.__name__ == 'RelatedManager':
                return [self.convert(item.pk) for item in obj.all()]
            elif isinstance(field, RelatedObject):
                return self.convert(obj.pk)
            raise
        if obj.__class__.__name__ == 'ManyRelatedManager':
            return [self.convert(item.pk) for item in obj.all()]
        return obj

    def revert_field(self, data, field_name, into):
        # Hack!
        into[field_name + '_id'] = self.revert(data.get(field_name))


# class ManyPrimaryKeyRelatedField(PrimaryKeyRelatedField):
#     def revert(self, value):
#         return [super(ManyPrimaryKeyRelatedField, self).revert(item)
#                 for item in value]


class NaturalKeyRelatedField(RelatedField):
    """
    Serializes a model related field or related manager to a natural key value.
    """
    is_natural_key = True  # XML renderer handles these differently

    def convert(self, obj):
        if hasattr(obj, 'natural_key'):
            return obj.natural_key()
        return obj


class PrimaryKeyOrNaturalKeyRelatedField(PrimaryKeyRelatedField):
    """
    Serializes to either pk or natural key, depending on if 'use_natural_keys'
    is specified when calling `serialize()`.
    """

    def convert_field(self, obj, field_name):
        if self.root.options.get('use_natural_keys', False):
            self.is_natural_key = True
            return self.convert_field_natural_key(obj, field_name)
        self.is_natural_key = False
        return super(PrimaryKeyOrNaturalKeyRelatedField, self).convert_field(obj, field_name)

    def convert_field_natural_key(self, obj, field_name):
        obj = getattr(obj, field_name)
        if obj.__class__.__name__ in ('RelatedManager', 'ManyRelatedManager'):
            return [self.convert_natural_key(item) for item in obj.all()]
        return self.convert_natural_key(obj)

    def convert_natural_key(self, obj):
        if hasattr(obj, 'natural_key'):
            return obj.natural_key()
        return obj


class ModelNameField(Field):
    """
    Serializes the model instance's model name.  Eg. 'auth.User'.
    """
    def convert_field(self, obj, field_name):
        return smart_unicode(obj._meta)

    def revert_field(self, data, field_name, into):
        # We don't actually want to restore the model name metadata to a field.
        pass


class BooleanField(ModelField):
    error_messages = {
        'invalid': _(u"'%s' value must be either True or False."),
    }

    def revert(self, value):
        if value in (True, False):
            # if value is 1 or 0 than it's equal to True or False, but we want
            # to return a true bool for semantic reasons.
            return bool(value)
        if value in ('t', 'True', '1'):
            return True
        if value in ('f', 'False', '0'):
            return False
        raise ValidationError(self.error_messages['invalid'] % value)


class CharField(ModelField):
    def revert(self, value):
        if isinstance(value, basestring) or value is None:
            return value
        return smart_unicode(value)


class DateField(ModelField):
    error_messages = {
        'invalid': _(u"'%s' value has an invalid date format. It must be "
                     u"in YYYY-MM-DD format."),
        'invalid_date': _(u"'%s' value has the correct format (YYYY-MM-DD) "
                          u"but it is an invalid date."),
    }

    def revert(self, value):
        if value is None:
            return value
        if isinstance(value, datetime.datetime):
            if settings.USE_TZ and timezone.is_aware(value):
                # Convert aware datetimes to the default time zone
                # before casting them to dates (#17742).
                default_timezone = timezone.get_default_timezone()
                value = timezone.make_naive(value, default_timezone)
            return value.date()
        if isinstance(value, datetime.date):
            return value

        try:
            parsed = parse_date(value)
            if parsed is not None:
                return parsed
        except ValueError:
            msg = self.error_messages['invalid_date'] % value
            raise ValidationError(msg)

        msg = self.error_messages['invalid'] % value
        raise ValidationError(msg)


class DateTimeField(ModelField):
    error_messages = {
        'invalid': _(u"'%s' value has an invalid format. It must be in "
                     u"YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ] format."),
        'invalid_date': _(u"'%s' value has the correct format "
                          u"(YYYY-MM-DD) but it is an invalid date."),
        'invalid_datetime': _(u"'%s' value has the correct format "
                              u"(YYYY-MM-DD HH:MM[:ss[.uuuuuu]][TZ]) "
                              u"but it is an invalid date/time."),
    }

    def revert(self, value):
        if value is None:
            return value
        if isinstance(value, datetime.datetime):
            return value
        if isinstance(value, datetime.date):
            value = datetime.datetime(value.year, value.month, value.day)
            if settings.USE_TZ:
                # For backwards compatibility, interpret naive datetimes in
                # local time. This won't work during DST change, but we can't
                # do much about it, so we let the exceptions percolate up the
                # call stack.
                warnings.warn(u"DateTimeField received a naive datetime (%s)"
                              u" while time zone support is active." % value,
                              RuntimeWarning)
                default_timezone = timezone.get_default_timezone()
                value = timezone.make_aware(value, default_timezone)
            return value

        try:
            parsed = parse_datetime(value)
            if parsed is not None:
                return parsed
        except ValueError:
            msg = self.error_messages['invalid_datetime'] % value
            raise ValidationError(msg)

        try:
            parsed = parse_date(value)
            if parsed is not None:
                return datetime.datetime(parsed.year, parsed.month, parsed.day)
        except ValueError:
            msg = self.error_messages['invalid_date'] % value
            raise ValidationError(msg)

        msg = self.error_messages['invalid'] % value
        raise ValidationError(msg)


class IntegerField(ModelField):
    error_messages = {
        'invalid': _(u"'%s' value must be an integer."),
    }

    def revert(self, value):
        if value in validators.EMPTY_VALUES:
            return None
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(self.error_messages['invalid'])
        return value


field_mapping = {
    models.AutoField: IntegerField,
    models.BooleanField: BooleanField,
    models.CharField: CharField,
    models.DateTimeField: DateTimeField,  # Needs to be before DateField!
    models.DateField: DateField,
    models.IntegerField: IntegerField,
    models.PositiveIntegerField: IntegerField
}


def modelfield_to_serializerfield(field):
    return field_mapping.get(type(field), ModelField)
