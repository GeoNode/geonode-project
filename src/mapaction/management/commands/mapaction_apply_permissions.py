"""Re-apply the agreed access rule to loaded maps: Public -> anyone; anything else -> signed-in users only.

  mapaction_apply_permissions [--shard i/n] [--dry-run]
"""
import zlib

from django.core.management.base import BaseCommand

from mapaction import services, vocab
from mapaction.models import MapVersion


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--shard")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, **o):
        qs = MapVersion.objects.select_related("resource").order_by("pk")
        counts = {"public": 0, "signed-in only": 0}
        for mv in qs.iterator():
            if o["shard"]:
                i, n = (int(x) for x in o["shard"].split("/"))
                if zlib.crc32(str(mv.pk).encode()) % n != i:
                    continue
            public = vocab.access_is_public(mv.metadata.get("access"))
            counts["public" if public else "signed-in only"] += 1
            if not o["dry_run"]:
                services.apply_permissions(mv.resource, public)
        self.stdout.write(", ".join(f"{k}: {v}" for k, v in counts.items()))
