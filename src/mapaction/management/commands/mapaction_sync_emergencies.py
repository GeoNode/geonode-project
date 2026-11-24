"""Create or update every Emergency (and its filter term) from the CKAN mirror's event list (data/ckan/catalog/events.json)."""
import json
import pathlib

from django.core.management.base import BaseCommand

from mapaction import services
from mapaction.models import Emergency


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--mirror", required=True)

    def handle(self, **o):
        events = json.loads((pathlib.Path(o["mirror"]) / "catalog" / "events.json").read_text())
        n = 0
        for ev in events:
            code, title = ev["name"], (ev.get("title") or ev.get("display_name") or ev["name"]).strip()
            em, _ = Emergency.objects.update_or_create(code=code, defaults={
                "title": title, "description": (ev.get("description") or "").strip(),
                "image_url": ev.get("image_display_url") or "", "source_url": f"https://maps.mapaction.org/event/{code}"})
            em.keyword = services.term("mapaction-emergency", code, title)
            em.save(update_fields=["keyword"])
            n += 1
        self.stdout.write(f"{n} emergencies synced")
