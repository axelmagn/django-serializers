
# Validation

There's some more work needed on validation.  Currently ValidationError will be thrown on first field validation failure.  Should instead work more like existing form validation, and include a dictionary of field errors.

ModelSerializer needs instance-level validation mirroring that of `ModelForm`.

Consider if we ought to have deserialization hooks that mirror the field clean methods on forms.  Eg `FOO_from_native` or `clean_FOO`, that performs cleaning & validation.

# Mapping model fields -> serializer fields

Currently all non-relational fields on a Model simply map to the `Field` class, which is able to generically handle the field, by having a `model_field` attribute that ties it back to the corrosponding model field.

Two issues here:

1. Model fields ought to instead get mapped to the correct `Field` subclass, which imply different validation behaviour.
2. Need to review how and when serializer fields get tied to model fields.  Ideally remove `.model_field`, but bear in mind that eg. `id` on fixture serializer needs to be able to determine the type of the pk field it should use.  `PrimaryKeyRelatedField` needs to be able to support both integer pk fields and non-integer pk fields.  `NaturalKeyRelatedField` needs to be able to get the correct manager class for the field it's pointed at.  Model fields with custom storage need to be properly supported.

# Deserializing lists vs instances

Serializer and ModelSerializer don't currently have any way of being tied to either an instance or a list of instances.  When serializing they'll descend into any container types, leave primatives as-is, and apply the serialization to the first object they come across.  That's fine for serialization, but it's awkward for deserialization. Really need to validate the incoming data.  Not obvious what the API for doing so should look like.

# Field options

Mirrot form fields more closely.

Currently `source`, `label`, `readonly`.  Needs `errors`, `validators`, either `required` or `blank`/`null`, and possibly `help_text`.

Other options for eg. `CharField` (`max_length` etc...)

# XML Rendering/parsing
