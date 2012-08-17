DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django-modeltests',
    'django-serializers-regress'
)

SERIALIZATION_MODULES = {
    "xml": "serializers.compat.xml",
    "python": "serializers.compat.python",
    "json": "serializers.compat.json",
    #"yaml": "serializers.compat.yaml"
}
