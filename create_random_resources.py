"""
Django management command to bulk-create random GeoNode resources
(Documents, Maps, and — best-effort — Datasets), for load/QA testing.

INSTALL
-------
Drop this file into any GeoNode app's management/commands package, e.g.:

    geonode/base/management/commands/create_random_resources.py

(create the `management/` and `management/commands/` dirs with empty
__init__.py files if they don't already exist).

WHAT IT DOES
------------
Creates --count resources spread across the requested --resource-type(s),
each with:
  - a random owner picked from existing active users
  - a random title/abstract (and random category/keywords if any exist
    in your instance)
  - Documents: a small synthetic in-memory file attached as doc_file
  - Maps: a Map object, optionally referencing a random existing Dataset
    as a MapLayer if any Datasets are present
  - Datasets: best-effort only. Creating a REAL dataset means importing
    actual vector/raster data through GeoServer, which this lightweight
    script does not do. Instead it uses GeoNode's own test-data helper
    (geonode.base.populate_test_data.create_single_dataset) to create
    DB-only fake dataset records, which is fine for exercising listings,
    search, and permissions, but these fake datasets will NOT render a
    real map/WMS preview. If that helper isn't importable in your GeoNode
    version, dataset creation is skipped with a warning and count/CSV
    reflect that.

Then, matching the other two scripts (create_bulk_users /
randomize_resource_permissions), it optionally applies the SAME random
permission logic on every resource it creates, via --randomize-permissions
and the identical --min-users/--max-users/--levels/--randomize-anonymous
options, so all three scripts compose together and log the same way.

USAGE
-----
    python manage.py create_random_resources --count 1000 \
        --resource-type document,map --randomize-permissions \
        --min-users 1 --max-users 5 --csv-out created_resources.csv

    # include experimental fake datasets too:
    python manage.py create_random_resources --count 50 \
        --resource-type document,map,dataset --dry-run

Options:
    --count                 N     total resources to create (default 1000)
    --resource-type         CSV   subset of document,map,dataset (default: document,map)
    --prefix                STR   title prefix (default "AutoResource")
    --include-superusers          allow superusers to be picked as random owners
    --seed                  N     random seed, for reproducible runs
    --csv-out               PATH  where to log created resources (default created_resources.csv)
    --dry-run                     compute everything but don't write to the DB

    Permission randomization (only applied if --randomize-permissions is set):
    --randomize-permissions       after creating each resource, randomly (re)assign
                                   permissions the same way randomize_resource_permissions does
    --min-users             N     min number of users to touch per resource (default 1)
    --max-users             N     max number of users to touch per resource (default 5)
    --levels                CSV   subset of view,download,edit,manage to sample from
    --randomize-anonymous          also randomly flip public/anonymous view access
"""

import csv
import random
import string
import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from geonode.base.models import ResourceBase, TopicCategory
from geonode.documents.models import Document
from geonode.maps.models import Map

User = get_user_model()

RESOURCE_TYPES = ["document", "map", "dataset"]

LEVELS = {
    "view": ["view_resourcebase"],
    "download": ["view_resourcebase", "download_resourcebase"],
    "edit": ["view_resourcebase", "download_resourcebase", "change_resourcebase", "change_resourcebase_metadata"],
    "manage": [
        "view_resourcebase",
        "download_resourcebase",
        "change_resourcebase",
        "change_resourcebase_metadata",
        "change_resourcebase_permissions",
        "delete_resourcebase",
    ],
}

WORD_POOL = [
    "river", "forest", "urban", "coastal", "seismic", "rainfall", "elevation",
    "landcover", "boundary", "soil", "wetland", "traffic", "population",
    "temperature", "vegetation", "flood", "geology", "cadastral", "network", "survey",
]


def random_words(n=3):
    return " ".join(random.choice(WORD_POOL) for _ in range(n))


def random_suffix(n=6):
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))


def apply_random_permissions(resource, users, levels, min_users, max_users, dry_run, rows):
    resource = resource.get_self_resource()
    n_users = random.randint(min_users, min(max_users, len(users))) if users else 0
    picked_users = random.sample(users, n_users) if n_users else []

    user_perm_spec = {}
    if resource.owner_id:
        user_perm_spec[resource.owner.username] = LEVELS["manage"]

    for user in picked_users:
        if resource.owner_id and user.id == resource.owner_id:
            continue
        level = random.choice(levels)
        user_perm_spec[user.username] = LEVELS[level]
        rows.append((resource.id, resource.title, user.username, level))

    perm_spec = {"users": user_perm_spec, "groups": {}}

    if not dry_run:
        resource.set_permissions(perm_spec)


class Command(BaseCommand):
    help = "Bulk-create random GeoNode resources (documents/maps/best-effort datasets) for load/QA testing."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=1000)
        parser.add_argument("--resource-type", type=str, default="document,map")
        parser.add_argument("--prefix", type=str, default="AutoResource")
        parser.add_argument("--include-superusers", action="store_true")
        parser.add_argument("--seed", type=int, default=None)
        parser.add_argument("--csv-out", type=str, default="created_resources.csv")
        parser.add_argument("--dry-run", action="store_true")

        # permission randomization, mirroring randomize_resource_permissions.py
        parser.add_argument("--randomize-permissions", action="store_true")
        parser.add_argument("--min-users", type=int, default=1)
        parser.add_argument("--max-users", type=int, default=5)
        parser.add_argument("--levels", type=str, default="view,download,edit,manage")
        parser.add_argument("--randomize-anonymous", action="store_true")

    def handle(self, *args, **opts):
        if opts["seed"] is not None:
            random.seed(opts["seed"])

        types = [t.strip() for t in opts["resource_type"].split(",") if t.strip()]
        for t in types:
            if t not in RESOURCE_TYPES:
                raise CommandError(f"Unknown resource type '{t}'. Valid: {', '.join(RESOURCE_TYPES)}")

        levels = [lvl.strip() for lvl in opts["levels"].split(",") if lvl.strip()]
        for lvl in levels:
            if lvl not in LEVELS:
                raise CommandError(f"Unknown level '{lvl}'. Valid: {', '.join(LEVELS)}")

        if opts["min_users"] > opts["max_users"]:
            raise CommandError("--min-users cannot be greater than --max-users")

        user_qs = User.objects.filter(is_active=True)
        if not opts["include_superusers"]:
            user_qs = user_qs.exclude(is_superuser=True)
        users = list(user_qs)
        if not users:
            raise CommandError("No candidate users found (check --include-superusers, "
                                "or run create_bulk_users.py first).")

        categories = list(TopicCategory.objects.all())
        existing_datasets = None  # lazy-loaded only if we're creating maps

        create_single_dataset = None
        if "dataset" in types:
            try:
                from geonode.base.populate_test_data import create_single_dataset as _csd
                create_single_dataset = _csd
            except ImportError:
                self.stdout.write(self.style.WARNING(
                    "geonode.base.populate_test_data.create_single_dataset not importable in this "
                    "GeoNode version — 'dataset' creation will be skipped. Use document/map instead, "
                    "or import real data through the normal GeoNode uploader for genuine datasets."
                ))

        rows = []          # created_resources.csv rows
        perm_rows = []      # permission assignment rows, if --randomize-permissions
        created_counts = {t: 0 for t in types}
        skipped_counts = {t: 0 for t in types}

        for i in range(1, opts["count"] + 1):
            rtype = random.choice(types)
            owner = random.choice(users)
            title = f"{opts['prefix']} {rtype} {random_words(2)} {i}"
            abstract = f"Auto-generated {rtype} for load testing: {random_words(6)}."
            category = random.choice(categories) if categories else None

            resource = None

            if opts["dry_run"]:
                created_counts[rtype] += 1
                rows.append((None, rtype, title, owner.username))
                continue

            try:
                with transaction.atomic():
                    if rtype == "document":
                        content = f"Synthetic test document {uuid.uuid4()}\n{abstract}".encode()
                        doc = Document(
                            title=title,
                            abstract=abstract,
                            owner=owner,
                            category=category,
                        )
                        doc.doc_file.save(f"{random_suffix()}.txt", ContentFile(content), save=False)
                        doc.save()
                        resource = doc

                    elif rtype == "map":
                        m = Map(
                            title=title,
                            abstract=abstract,
                            owner=owner,
                            category=category,
                            zoom=random.randint(1, 18),
                            center_x=round(random.uniform(-180, 180), 4),
                            center_y=round(random.uniform(-85, 85), 4),
                            projection="EPSG:3857",
                        )
                        m.save()
                        resource = m
                        # best-effort: attach a random existing dataset as a layer, if any exist
                        if existing_datasets is None:
                            from geonode.layers.models import Dataset
                            existing_datasets = list(Dataset.objects.all()[:200])
                        if existing_datasets:
                            try:
                                from geonode.maps.models import MapLayer
                                ds = random.choice(existing_datasets)
                                MapLayer.objects.create(
                                    map=m,
                                    name=ds.alternate if hasattr(ds, "alternate") else ds.name,
                                    ows_url=getattr(ds, "ows_url", "") or "",
                                    stack_order=0,
                                    visibility=True,
                                )
                            except Exception:
                                pass  # non-fatal — map still created without a layer

                    elif rtype == "dataset":
                        if not create_single_dataset:
                            skipped_counts[rtype] += 1
                            continue
                        ds = create_single_dataset(f"{opts['prefix'].lower()}_{random_suffix()}")
                        ds.title = title
                        ds.abstract = abstract
                        ds.owner = owner
                        if category:
                            ds.category = category
                        ds.save()
                        resource = ds

            except Exception as exc:
                skipped_counts[rtype] += 1
                self.stdout.write(self.style.WARNING(f"Skipped a {rtype} ({title!r}): {exc}"))
                continue

            created_counts[rtype] += 1
            rows.append((resource.id, rtype, title, owner.username))

            if opts["randomize_permissions"]:
                apply_random_permissions(
                    resource, users, levels, opts["min_users"], opts["max_users"],
                    opts["dry_run"], perm_rows,
                )
                if opts["randomize_anonymous"] and not opts["dry_run"]:
                    resource = resource.get_self_resource()
                    if random.choice([True, False]):
                        resource.set_permissions({"users": {"AnonymousUser": LEVELS["view"]}, "groups": {}})
                        perm_rows.append((resource.id, resource.title, "AnonymousUser", "view"))

            total_done = sum(created_counts.values())
            if total_done % 100 == 0:
                self.stdout.write(f"...created {total_done}/{opts['count']} resources")

        if rows:
            with open(opts["csv_out"], "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["resource_id", "resource_type", "title", "owner"])
                writer.writerows(rows)
            self.stdout.write(self.style.SUCCESS(f"Logged {len(rows)} created resources to {opts['csv_out']}"))

        if perm_rows:
            perm_csv = "perm_" + opts["csv_out"]
            with open(perm_csv, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["resource_id", "resource_title", "username", "level"])
                writer.writerows(perm_rows)
            self.stdout.write(self.style.SUCCESS(f"Logged {len(perm_rows)} permission assignments to {perm_csv}"))

        mode = "DRY RUN — no changes were saved" if opts["dry_run"] else "changes applied"
        self.stdout.write(self.style.SUCCESS(
            f"Done ({mode}). Created: {created_counts}. Skipped: {skipped_counts}."
        ))
