import os

from django.apps import AppConfig

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


class MapActionConfig(AppConfig):
    name = "mapaction"
    verbose_name = "MapAction maps"
    default_auto_field = "django.db.models.AutoField"

    def ready(self):
        from django.conf import settings

        from . import api

        # MapAction's geonode-mapstore-client snippets (navbar, footer, theme, catalogue config) replace the
        # Kartoza defaults. kartoza_geonode puts its own templates first in DIRS when it starts; this app is
        # installed after it, so moving ours to the front here keeps the Kartoza files untouched.
        dirs = settings.TEMPLATES[0]["DIRS"]
        while TEMPLATES_DIR in dirs:
            dirs.remove(TEMPLATES_DIR)
        dirs.insert(0, TEMPLATES_DIR)

        api.install()
