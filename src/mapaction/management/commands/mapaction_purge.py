"""Delete loaded maps (their GeoNode records, files and version rows). Dry run unless --apply.

  mapaction_purge --emergency 2006-idn-001 [--emergency ...] [--apply]
  mapaction_purge --all-except 2026-mdg-001 --all-except 2023-per-001 [--apply]
"""
from django.core.management.base import BaseCommand, CommandError

from geonode.resource.manager import resource_manager

from mapaction.models import Emergency, MapSeries, MapVersion


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--emergency", action="append", default=[])
        parser.add_argument("--all-except", action="append", default=[])
        parser.add_argument("--no-emergency", action="store_true", help="maps loaded without an emergency")
        parser.add_argument("--apply", action="store_true")

    def handle(self, **o):
        if not (o["emergency"] or o["all_except"] or o["no_emergency"]):
            raise CommandError("give --emergency, --all-except or --no-emergency")
        qs = MapVersion.objects.select_related("series__emergency", "resource")
        if o["emergency"]:
            qs = qs.filter(series__emergency__code__in=o["emergency"])
        if o["no_emergency"]:
            qs = qs.filter(series__emergency__isnull=True)
        if o["all_except"]:
            qs = qs.exclude(series__emergency__code__in=o["all_except"])
        n = qs.count()
        self.stdout.write(f"{n} map versions {'deleting' if o['apply'] else 'would be deleted'}")
        if not o["apply"]:
            return
        for mv in qs:
            for f in mv.files.exclude(file=""):
                f.file.delete(save=False)
            doc = mv.resource
            resource_manager.delete(doc.uuid, instance=doc)
        MapSeries.objects.filter(versions__isnull=True).delete()
        Emergency.objects.filter(series__isnull=True).delete()
        self.stdout.write("done")
