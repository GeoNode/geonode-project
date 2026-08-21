"""
Django management command to create N *real* GeoNode Datasets: generates
random GeoJSON/GeoTIFF files and pushes them through GeoNode's actual
upload/import pipeline (geonode.upload), so each Dataset is a genuine
GeoServer-registered layer, not a DB-only fake.

INSTALL
-------
Already in this project's own app (geonode_project) — nothing to drop in,
it's live via the volume mount:

    geonode_project/management/commands/create_real_datasets.py

USAGE
-----
    python manage.py create_real_datasets --count 20 --prefix loadtest \
        --min-features 10 --max-features 5000 --csv-out real_datasets.csv

    # rasters only, small run, verbose:
    python manage.py create_real_datasets --count 5 --type raster

Options:
    --count           N     how many datasets to create (default 20)
    --type            vector|raster|both   (default: both, random per dataset)
    --prefix          STR   title/filename prefix (default "loadtest_dataset")
    --min-features    N     min features per vector dataset (default 10)
    --max-features    N     max features per vector dataset (default 5000)
    --raster-size     N     raster width/height in pixels (default 32)
    --owner           STR   username to own the datasets (default: first superuser)
    --work-dir         PATH directory to write generated files into before
                             import — MUST be visible to the celery worker
                             container too (default: /tmp, which this
                             project's docker-compose shares between the
                             django and celery containers)
    --timeout         N     seconds to wait for each import before giving up
                             (default 300) — a per-dataset timeout, not a
                             failure: the import keeps running server-side
    --seed            N     random seed, for reproducible generation
    --csv-out         PATH  where to log created datasets (default created_datasets.csv)
    --dry-run                only generate files locally, skip the import entirely

IDEMPOTENCY / RELIABILITY
--------------------------
Each generated file (and the Dataset title derived from it) gets a unique
suffix, so re-running never collides with a previous run's names. Every
dataset's outcome (success/failure/timeout) is reported individually and
logged to the CSV with a status column — there is no silent partial state:
a dataset either finished importing (and is in GeoServer) or it is logged
as failed/timed-out and simply not counted as created.
"""

import csv
import os
import random
import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from geonode_project.management.geo_generators import generate_random_geojson, generate_random_geotiff
from geonode_project.management.importer_bridge import ImportFailed, ImportTimedOut, import_and_wait

User = get_user_model()


class Command(BaseCommand):
    help = "Create N real Datasets (vector + raster) by generating test files and running them through GeoNode's real upload/import pipeline."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=20)
        parser.add_argument("--type", choices=["vector", "raster", "both"], default="both")
        parser.add_argument("--prefix", type=str, default="loadtest_dataset")
        parser.add_argument("--min-features", type=int, default=10)
        parser.add_argument("--max-features", type=int, default=5000)
        parser.add_argument("--raster-size", type=int, default=32)
        parser.add_argument("--owner", type=str, default=None)
        parser.add_argument("--work-dir", type=str, default="/tmp")
        parser.add_argument("--timeout", type=int, default=300)
        parser.add_argument("--seed", type=int, default=None)
        parser.add_argument("--csv-out", type=str, default="created_datasets.csv")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        if opts["seed"] is not None:
            random.seed(opts["seed"])

        owner = self._resolve_owner(opts["owner"])
        self.stdout.write(f"Owner for generated datasets: {owner.username}")

        rows = []
        created, failed = 0, 0

        for i in range(1, opts["count"] + 1):
            kind = opts["type"] if opts["type"] != "both" else random.choice(["vector", "raster"])
            token = uuid.uuid4().hex[:10]
            title = f"{opts['prefix']} {kind} {token}"

            try:
                file_path, detail = self._generate_file(kind, opts, token)
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"[{i}/{opts['count']}] generation failed for {title!r}: {exc}"))
                rows.append((title, kind, detail if opts["dry_run"] else "", "generation_failed", str(exc)))
                failed += 1
                continue

            self.stdout.write(f"[{i}/{opts['count']}] generated {kind} ({detail}) -> {file_path}")

            if opts["dry_run"]:
                rows.append((title, kind, detail, "dry_run", ""))
                created += 1
                continue

            try:
                resource = import_and_wait(file_path, owner, title=title, timeout=opts["timeout"])
                # the import pipeline names/owns the resource from the file itself —
                # force our intended title/owner so it matches what's logged to the CSV
                resource.title = title
                resource.abstract = f"Auto-generated {kind} dataset for load testing ({detail})."
                resource.owner = owner
                resource.save()
                self.stdout.write(self.style.SUCCESS(
                    f"[{i}/{opts['count']}] imported OK: dataset id={resource.id} alternate={getattr(resource, 'alternate', '?')}"
                ))
                rows.append((title, kind, detail, "created", str(resource.id)))
                created += 1
            except (ImportFailed, ImportTimedOut) as exc:
                self.stdout.write(self.style.WARNING(f"[{i}/{opts['count']}] import failed for {title!r}: {exc}"))
                rows.append((title, kind, detail, "import_failed", str(exc)))
                failed += 1
            finally:
                try:
                    os.remove(file_path)
                except OSError:
                    pass

        if rows:
            with open(opts["csv_out"], "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["title", "type", "detail", "status", "result"])
                writer.writerows(rows)
            self.stdout.write(self.style.SUCCESS(f"Logged {len(rows)} attempts to {opts['csv_out']}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Created: {created}, Failed: {failed}."))

    def _resolve_owner(self, username):
        if username:
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f"--owner user '{username}' does not exist")
        owner = User.objects.filter(is_superuser=True, is_active=True).order_by("id").first()
        if not owner:
            raise CommandError("No active superuser found — pass --owner explicitly")
        return owner

    def _generate_file(self, kind, opts, token):
        if kind == "vector":
            path = os.path.join(opts["work_dir"], f"{opts['prefix']}_{token}.geojson")
            _, n_features, geom_type = generate_random_geojson(
                path, min_features=opts["min_features"], max_features=opts["max_features"]
            )
            return path, f"{n_features} {geom_type} features"

        path = os.path.join(opts["work_dir"], f"{opts['prefix']}_{token}.tif")
        _, width, height = generate_random_geotiff(path, width=opts["raster_size"], height=opts["raster_size"])
        return path, f"{width}x{height} raster"
