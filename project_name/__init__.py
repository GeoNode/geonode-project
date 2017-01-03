import os

__version__ = (2, 5, 7, 'alpha', 0)


class GeoNodeException(Exception):
    """Base class for exceptions in this module."""
    pass


def get_version():
    import {{ project_name }}.version
    return {{ project_name }}.version.get_version(__version__)


def main(global_settings, **settings):
    from django.core.wsgi import get_wsgi_application
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings.get('django_settings'))
    app = get_wsgi_application()
    return app
