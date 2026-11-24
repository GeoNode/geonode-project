from django.core.management.base import BaseCommand

from mapaction import services


class Command(BaseCommand):
    help = "Create MapAction's filter vocabularies (thesauri) and the service account that owns loaded maps."

    def handle(self, **options):
        thesauri = services.setup_vocabularies()
        user = services.service_account()
        for ident, t in thesauri.items():
            self.stdout.write(f"thesaurus {ident}: {t.title} (order {t.order}, {t.thesaurus.count()} terms)")
        self.stdout.write(f"service account: {user.username} <{user.email}>")
        self.stdout.write("Restart GeoNode once so the catalogue picks up new filters.")
