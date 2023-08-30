import os
from django.apps import AppConfig
from django.conf.urls import include, url
from django.db.models import Max

import logging
logger = logging.getLogger(__name__)


def run_setup_hooks(*args, **kwargs):
    from django.conf import settings
    from geonode.urls import urlpatterns
    from geonode.base.models import Menu, MenuItem, MenuPlaceholder

    # implement some setup hooks, adjust urls, etc. ...
    pass


class SampleAppConfig(AppConfig):
    name = 'sample_app'
    type = 'GEONODE_APP'

    def ready(self):
        super().ready()
        run_setup_hooks()


default_app_config = 'sample_app.SampleAppConfig'
