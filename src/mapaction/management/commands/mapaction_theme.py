"""Apply MapAction's home-page banner as a GeoNode theme: the same one as on mapaction.geospatialhosting.com
(image, title, text and CSS from other/styling/apply_style.py). Safe to re-run."""
import pathlib

from django.core.files import File
from django.core.management.base import BaseCommand

from geonode.themes.models import GeoNodeThemeCustomization

STATIC = pathlib.Path(__file__).resolve().parents[2] / "static" / "mapaction"
NAME = "MapAction"
TITLE = "Mapping for people in crisis"
CONTENT = ("Maps and data from MapAction's emergency responses. "
           "This is a test site, so the content and the look are still changing.")


class Command(BaseCommand):
    help = __doc__

    def handle(self, **options):
        theme, created = GeoNodeThemeCustomization.objects.get_or_create(name=NAME, defaults={
            "description": "Placeholder banner (cut from MA066: needs a credit or a replacement)"})
        theme.welcome_theme = "JUMBOTRON_BG"
        theme.jumbotron_welcome_title = TITLE
        theme.jumbotron_welcome_content = CONTENT
        theme.extra_css = (STATIC / "theme-extra.css").read_text()
        if not theme.jumbotron_bg:
            with open(STATIC / "banner.jpg", "rb") as fh:
                theme.jumbotron_bg.save("mapaction-banner.jpg", File(fh), save=False)
        theme.is_enabled = True
        theme.save()
        GeoNodeThemeCustomization.objects.exclude(pk=theme.pk).update(is_enabled=False)
        self.stdout.write(f"{'created' if created else 'updated'} theme {NAME!r} (enabled)")
