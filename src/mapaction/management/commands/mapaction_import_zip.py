"""Load MapAction product ZIPs (PDF + JPG + XML from the ArcGIS add-on, atlas sheets included).

  mapaction_import_zip path/to/product.zip [more.zip | folder | zip-of-zips] [--apply]
"""
import io
import pathlib
import zipfile

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from mapaction import extract, services


def read_products(path):
    """(zip name, {member basename: bytes}) per product: a product ZIP, a zip of zips, or a folder of either."""
    path = pathlib.Path(path)
    if path.is_dir():
        for p in sorted(path.rglob("*.zip")):
            yield from read_products(p)
        return
    yield from extract.read_zip_products(path.name, path.read_bytes())


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="+")
        parser.add_argument("--apply", action="store_true", help="really load; default is a dry run")
        parser.add_argument("--user", help="who is running the load (kept for staff only)")

    def handle(self, **o):
        loaded_by = get_user_model().objects.filter(username=o["user"]).first() if o["user"] else None
        for path in o["paths"]:
            for name, members in read_products(path):
                try:
                    p = extract.from_zip(name, members)
                    mv, action = services.publish(p, loaded_by=loaded_by, dry_run=not o["apply"])
                except Exception as e:
                    self.stdout.write(f"error        {name}: {e}")
                    continue
                sheets = sum(1 for f in p.files if f.role == "sheet")
                self.stdout.write(f"{action:<12} {name:<50} {p.display_title[:60]}" + (f"  [{sheets} sheets]" if sheets else ""))
                for w in p.warnings:
                    self.stdout.write(f"{'':12} note: {w}")
