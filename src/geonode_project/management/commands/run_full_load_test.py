"""
Single Django management command that runs the full load-test pipeline:

    1) create N users
    2) create M random resources (documents/maps, best-effort datasets)
    3) randomly (re)assign permissions across resources

INSTALL
-------
Drop this file into any GeoNode app's management/commands package, e.g.:

    geonode/base/management/commands/run_full_load_test.py

(create the `management/` and `management/commands/` dirs with empty
__init__.py files if they don't already exist).

USAGE
-----
    python manage.py run_full_load_test \
        --num-users 1000 \
        --num-resources 1000 --resource-type document,map \
        --min-users 1 --max-users 5 \
        --csv-out-prefix load_test

    # preview only, nothing written to the DB:
    python manage.py run_full_load_test --num-users 20 --num-resources 20 --dry-run

Everything is printed to the console as it happens (stage banners, batch
progress every 100 items, and a final summary table) so you can follow the
run live or pipe it to a logfile with e.g. `... | tee load_test.log`.

KEY OPTIONS
-----------
Users (stage 1):
    --num-users        N     how many users to create (default 1000)
    --user-prefix      STR   username/email prefix (default "testuser")
    --user-domain      STR   email domain (default "example.com")
    --user-password    STR   fixed password for all new users (random per-user if omitted)
    --user-start       N     starting numeric suffix (default 1)
    --group            STR   existing group to add new users to (optional)

Resources (stage 2):
    --num-resources    N     how many resources to create (default 1000)
    --resource-type    CSV   subset of document,map,dataset (default "document,map")
    --resource-prefix  STR   title prefix (default "AutoResource")
    --generate-thumbnails    generate real thumbnails per map/document (off by default —
                            each one is a synchronous GeoServer WMS render / celery task,
                            very slow at load-test volumes)

Permissions (stage 3):
    --min-users        N     min users touched per resource (default 1)
    --max-users        N     max users touched per resource (default 5)
    --levels           CSV   subset of view,download,edit,manage (default all four)
    --randomize-anonymous   also randomly flip public/anonymous view access
    --permissions-scope     "created" = only resources this run just made (default)
                            "all"     = every ResourceBase in the instance

Shared:
    --include-superusers    allow superusers to be picked as owners / permission subjects
    --seed             N     random seed, for reproducible runs
    --csv-out-prefix   STR   base filename for the 3 CSV logs written
                             (<prefix>_users.csv, <prefix>_resources.csv, <prefix>_permissions.csv)
    --dry-run                compute everything, print it, but write nothing to the DB
"""

import csv
import os
import random
import string
import time
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from geonode.base.models import ResourceBase, TopicCategory
from geonode.documents.models import Document
from geonode.maps.models import Map, MapLayer
from geonode.resource.registry import document_manager, map_manager

from geonode_project.management.geo_generators import generate_random_geojson, generate_random_geotiff
from geonode_project.management.importer_bridge import import_and_wait

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

# MapStore reads its viewer config from ResourceBase.blob (a plain JSONField), not from
# the MapLayer rows — those are just GeoNode-side bookkeeping (permissions cascade,
# map.datasets). A Map created without a blob has nothing for the viewer to render:
# no layers, no center/zoom. This is a minimal-but-real blob (mirrors what MapStore
# itself POSTs on save), one background layer plus one wms entry per attached Dataset.
MAP_BACKGROUND_LAYER = {
    "id": "mapnik__0",
    "name": "mapnik",
    "type": "osm",
    "group": "background",
    "title": "Open Street Map",
    "source": "osm",
    "visibility": True,
    "singleTile": False,
    "hidden": False,
}


def qualified_style_name(ds):
    """Workspace-qualified style name, e.g. "geonode:airports" — matches what real
    MapLayer.current_style / blob layer "style" entries actually contain."""
    if not ds.default_style:
        return None
    return f"{ds.workspace}:{ds.default_style.name}" if ds.workspace else ds.default_style.name


def build_map_blob(datasets, ows_url):
    """Build a minimal MapStore blob for a Map that renders `datasets` as WMS layers."""
    extents = [ds.ll_bbox_polygon.extent for ds in datasets if ds.ll_bbox_polygon]
    if extents:
        minx = min(e[0] for e in extents)
        miny = min(e[1] for e in extents)
        maxx = max(e[2] for e in extents)
        maxy = max(e[3] for e in extents)
    else:
        minx, miny, maxx, maxy = -180, -90, 180, 90

    width = maxx - minx
    zoom = 1
    for threshold in (90, 40, 20, 10, 5, 2, 1):
        if width <= threshold:
            zoom += 1
    center = {"x": (minx + maxx) / 2, "y": (miny + maxy) / 2, "crs": "EPSG:4326"}

    layers = [dict(MAP_BACKGROUND_LAYER)]
    for ds in datasets:
        layer_id = str(uuid.uuid4())
        bbox = ds.ll_bbox_polygon.extent if ds.ll_bbox_polygon else (minx, miny, maxx, maxy)
        style = qualified_style_name(ds) or ""
        layers.append({
            "id": layer_id,
            "url": ows_url,
            "bbox": {
                "crs": "EPSG:4326",
                "bounds": {"minx": bbox[0], "miny": bbox[1], "maxx": bbox[2], "maxy": bbox[3]},
            },
            "name": ds.alternate,
            "type": "wms",
            "style": style,
            "title": ds.title,
            "format": "image/png",
            "hidden": False,
            "visibility": True,
            "singleTile": False,
            "extendedParams": {"pk": str(ds.pk), "alternate": ds.alternate},
        })

    return {
        "version": 2,
        "map": {
            "zoom": zoom,
            "units": "m",
            "center": center,
            "groups": [{"id": "Default", "title": "Default", "expanded": True, "visibility": True}],
            "layers": layers,
            "maxExtent": [-20037508.34, -20037508.34, 20037508.34, 20037508.34],
            "projection": "EPSG:3857",
            "backgrounds": [],
            "visualizationMode": "2D",
        },
        "catalogServices": {
            "services": {
                "GeoNode": {
                    "url": "/",
                    "type": "geonode",
                    "title": "GeoNode",
                    "autoload": True,
                    "resourceTypes": ["dataset", "document", "map"],
                }
            },
            "selectedService": "GeoNode",
        },
    }, (minx, miny, maxx, maxy)


WORD_POOL = [
    "river", "forest", "urban", "coastal", "seismic", "rainfall", "elevation",
    "landcover", "boundary", "soil", "wetland", "traffic", "population",
    "temperature", "vegetation", "flood", "geology", "cadastral", "network", "survey",
]


def random_words(n=3):
    return " ".join(random.choice(WORD_POOL) for _ in range(n))


def random_suffix(n=6):
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))


def format_duration(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{seconds:02d}s"
    if minutes:
        return f"{minutes}m{seconds:02d}s"
    return f"{seconds}s"


def random_password(length=12):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choice(alphabet) for _ in range(length))


def model_field_names(model):
    """Field names actually present on this model in the running GeoNode version."""
    return {f.name for f in model._meta.get_fields()}


def find_file_field_name(model):
    """Find the first FileField (or subclass, e.g. ImageField) on a model, if any."""
    from django.db.models import FileField
    for f in model._meta.get_fields():
        if isinstance(f, FileField):
            return f.name
    return None


class Command(BaseCommand):
    help = "Full load-test pipeline: create users -> create random resources -> randomize permissions."

    def add_arguments(self, parser):
        # stage 1 - users
        parser.add_argument("--num-users", type=int, default=1000)
        parser.add_argument("--user-prefix", type=str, default="testuser")
        parser.add_argument("--user-domain", type=str, default="example.com")
        parser.add_argument("--user-password", type=str, default=None)
        parser.add_argument("--user-start", type=int, default=1)
        parser.add_argument("--group", type=str, default=None)

        # stage 2 - resources
        parser.add_argument("--num-resources", type=int, default=1000)
        parser.add_argument("--resource-type", type=str, default="document,map")
        parser.add_argument("--resource-prefix", type=str, default="AutoResource")
        # real dataset generation (only used when "dataset" is in --resource-type)
        parser.add_argument("--dataset-work-dir", type=str, default="/tmp")
        parser.add_argument("--dataset-min-features", type=int, default=10)
        parser.add_argument("--dataset-max-features", type=int, default=5000)
        parser.add_argument("--dataset-raster-size", type=int, default=32)
        parser.add_argument("--dataset-timeout", type=int, default=300)
        # maps reference real datasets: --min-layers to --max-layers each
        parser.add_argument("--min-layers", type=int, default=2)
        parser.add_argument("--max-layers", type=int, default=50)
        # map_manager/document_manager.create() generate a real thumbnail per resource
        # (a synchronous GeoServer WMS render per map, a synchronous celery .apply() per
        # document) — very slow at load-test volumes. Off by default; pass this to get
        # real thumbnails at the cost of a lot of wall-clock time.
        parser.add_argument("--generate-thumbnails", action="store_true")

        # stage 3 - permissions
        parser.add_argument("--min-users", type=int, default=1)
        parser.add_argument("--max-users", type=int, default=5)
        parser.add_argument("--levels", type=str, default="view,download,edit,manage")
        parser.add_argument("--randomize-anonymous", action="store_true")
        parser.add_argument("--permissions-scope", choices=["created", "all"], default="created")

        # shared
        parser.add_argument("--include-superusers", action="store_true")
        parser.add_argument("--seed", type=int, default=None)
        parser.add_argument("--csv-out-prefix", type=str, default="load_test")
        parser.add_argument("--dry-run", action="store_true")

    # ---------- small logging helper (plain print, prefixed by stage) ----------
    def log(self, stage, msg, level="INFO"):
        style = {"INFO": self.style.NOTICE, "WARN": self.style.WARNING, "ERROR": self.style.ERROR}.get(level, str)
        self.stdout.write(style(f"[{stage:^11}] {msg}"))

    def handle(self, *args, **opts):
        run_start = time.monotonic()

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

        if opts["min_layers"] > opts["max_layers"]:
            raise CommandError("--min-layers cannot be greater than --max-layers")

        dry_run = opts["dry_run"]

        self.log("SETUP", "=" * 60)
        self.log("SETUP", f"num_users={opts['num_users']} num_resources={opts['num_resources']} "
                           f"resource_type={types} min_users={opts['min_users']} max_users={opts['max_users']} "
                           f"levels={levels} scope={opts['permissions_scope']} dry_run={dry_run}")
        self.log("SETUP", "=" * 60)

        # ================= STAGE 1: USERS =================
        users_start = time.monotonic()
        self.log("USERS", f"Creating {opts['num_users']} users "
                           f"(prefix={opts['user_prefix']!r}, domain={opts['user_domain']!r}) ...")

        group = None
        if opts["group"]:
            group = Group.objects.filter(name=opts["group"]).first()
            if not group:
                self.log("USERS", f"Group '{opts['group']}' not found — users created without a group.", "WARN")

        created_users, skipped_users, user_rows = [], [], []

        with transaction.atomic():
            for i in range(opts["user_start"], opts["user_start"] + opts["num_users"]):
                username = f"{opts['user_prefix']}{i}"
                email = f"{opts['user_prefix']}{i}@{opts['user_domain']}"

                if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
                    skipped_users.append(username)
                    continue

                password = opts["user_password"] or random_password()

                if not dry_run:
                    user = User.objects.create_user(username=username, email=email, password=password)
                    user.is_active = True
                    user.save(update_fields=["is_active"])
                    if group:
                        user.groups.add(group)

                created_users.append(username)
                user_rows.append((username, email, password))

                if len(created_users) % 100 == 0:
                    self.log("USERS", f"...{len(created_users)}/{opts['num_users']} users created")

            if dry_run:
                transaction.set_rollback(True)

        self.log("USERS", f"Done. Created: {len(created_users)}, Skipped (already existed): {len(skipped_users)} "
                           f"[{format_duration(time.monotonic() - users_start)}]")

        # ================= build the user pool used for owners / permission subjects =================
        user_qs = User.objects.filter(is_active=True)
        if not opts["include_superusers"]:
            user_qs = user_qs.exclude(is_superuser=True)
        if dry_run:
            # in dry-run nothing new was persisted, so fall back to whatever already exists
            all_users = list(user_qs)
        else:
            all_users = list(user_qs.filter(username__in=created_users)) or list(user_qs)

        if not all_users:
            raise CommandError("No candidate users available for resource ownership / permissions "
                                "(check --include-superusers, or that user creation actually ran).")
        self.log("USERS", f"Owner/permission candidate pool size: {len(all_users)}")

        # ================= STAGE 2: RESOURCES =================
        resources_start = time.monotonic()
        self.log("RESOURCES", f"Creating {opts['num_resources']} resources of type(s) {types} ...")

        if not opts["generate_thumbnails"] and not dry_run:
            # map_manager/document_manager.create() unconditionally call set_thumbnail(),
            # which is a synchronous GeoServer WMS render per map / synchronous celery
            # .apply() per document — no-op it for this run's process only.
            from geonode.resource.manager import BaseResourceManager
            BaseResourceManager.set_thumbnail = lambda self, *a, **kw: False
            self.log("RESOURCES", "Thumbnail generation disabled for this run "
                                   "(pass --generate-thumbnails to enable; adds a per-resource "
                                   "GeoServer/WMS round-trip and will be much slower).", "WARN")

        categories = list(TopicCategory.objects.all())
        existing_datasets = None
        ows_url = None

        # introspect the actual Document fields available in this GeoNode version,
        # since these have changed across releases (e.g. Document's file field name)
        document_fields = model_field_names(Document)
        document_file_field = find_file_field_name(Document)
        warned_doc_file = False

        if document_file_field is None:
            self.log("RESOURCES", "No FileField found on the Document model in this GeoNode version — "
                                   "documents will be created as metadata-only "
                                   "(using doc_url if available, otherwise no file at all).", "WARN")

        created_counts = {t: 0 for t in types}
        skipped_counts = {t: 0 for t in types}
        resource_rows = []
        created_resources = []  # actual resource objects, used for stage 3 scope="created"

        for i in range(1, opts["num_resources"] + 1):
            rtype = random.choice(types)
            owner = random.choice(all_users)
            title = f"{opts['resource_prefix']} {rtype} {random_words(2)} {i}"
            abstract = f"Auto-generated {rtype} for load testing: {random_words(6)}."
            category = random.choice(categories) if categories else None

            if dry_run:
                created_counts[rtype] += 1
                resource_rows.append((None, rtype, title, owner.username))
                continue

            resource = None
            try:
                if rtype == "document":
                    # go through document_manager.create() (not a raw Document().save()) so
                    # subtype/extension detection, the asset+Link row, poc/metadata_author,
                    # default owner-only permissions and thumbnailing all actually run —
                    # see geonode.documents.manager.DocumentResourceManager.create()
                    doc_defaults = dict(title=title, abstract=abstract, owner=owner, category=category)
                    file_path = None
                    try:
                        if document_file_field:
                            file_path = os.path.join("/tmp", f"{random_suffix()}.txt")
                            content = f"Synthetic test document {uuid.uuid4()}\n{abstract}".encode()
                            with open(file_path, "wb") as fh:
                                fh.write(content)
                            doc = document_manager.create(
                                str(uuid.uuid4()), defaults=doc_defaults, file=file_path, user=owner,
                            )
                        else:
                            if "doc_url" in document_fields:
                                doc_defaults["doc_url"] = f"https://example.com/fake-doc-{random_suffix()}.txt"
                            doc = document_manager.create(str(uuid.uuid4()), defaults=doc_defaults, user=owner)
                        resource = doc
                    finally:
                        if file_path:
                            try:
                                os.remove(file_path)
                            except OSError:
                                pass

                elif rtype == "map":
                    # build 2..50 real, already-imported Datasets as *unsaved* MapLayers and
                    # hand them to map_manager.create() via the "maplayers" default — the manager
                    # attaches them with instance.maplayers.set(...) as part of create(), which is
                    # also what triggers bbox/extent recompute from the attached layers. A map with
                    # zero layers (no Datasets created yet) is still a usable resource, just warned.
                    if existing_datasets is None:
                        from geonode.layers.models import Dataset
                        existing_datasets = list(Dataset.objects.all())

                    if ows_url is None:
                        from geonode.geoserver.helpers import ogc_server_settings
                        ows_url = ogc_server_settings.public_url.rstrip("/") + "/ows"

                    maplayers = []
                    chosen = []
                    if existing_datasets:
                        n_layers = min(
                            random.randint(opts["min_layers"], opts["max_layers"]),
                            len(existing_datasets),
                        )
                        chosen = random.sample(existing_datasets, n_layers)
                        for order, ds in enumerate(chosen):
                            # map=None: MapLayer.map is nullable, and instance.maplayers.set()
                            # below needs objects with a pk to diff against the existing set —
                            # unsaved instances are unhashable ("without primary key value").
                            # store/ows_url left None to match what real MapStore-created
                            # MapLayers actually persist (the URL/store live in the blob layer,
                            # not here).
                            ml = MapLayer(
                                dataset=ds,
                                name=ds.alternate,
                                current_style=qualified_style_name(ds),
                                local=True,
                                order=order,
                                visibility=True,
                                opacity=1.0,
                            )
                            ml.save()
                            maplayers.append(ml)
                    else:
                        self.log("RESOURCES", f"No real Datasets exist yet — map {title!r} created with "
                                               f"zero layers (create 'dataset' resources first, or in the "
                                               f"same run before maps get their random turn).", "WARN")

                    # the MapLayer rows above are GeoNode-side bookkeeping only — what the
                    # MapStore viewer actually renders (layers, background, center/zoom) comes
                    # from the blob JSON, so build one instead of leaving it {} (default).
                    blob, bbox = build_map_blob(chosen, ows_url)

                    # mirrors MapViewSet.perform_create(): explicit resource_type="map" in the
                    # payload plus resource_type=Map as the model class to create.
                    m = map_manager.create(
                        str(uuid.uuid4()),
                        resource_type=Map,
                        defaults=dict(
                            title=title, abstract=abstract, owner=owner, category=category,
                            resource_type="map", maplayers=maplayers, blob=blob,
                            extent={"srid": "EPSG:4326", "coords": list(bbox)},
                        ),
                        user=owner,
                    )
                    resource = m

                elif rtype == "dataset":
                    kind = random.choice(["vector", "raster"])
                    token = uuid.uuid4().hex[:10]
                    try:
                        if kind == "vector":
                            file_path = os.path.join(opts["dataset_work_dir"], f"{opts['resource_prefix']}_{token}.geojson")
                            generate_random_geojson(
                                file_path,
                                min_features=opts["dataset_min_features"],
                                max_features=opts["dataset_max_features"],
                            )
                        else:
                            file_path = os.path.join(opts["dataset_work_dir"], f"{opts['resource_prefix']}_{token}.tif")
                            generate_random_geotiff(file_path, width=opts["dataset_raster_size"], height=opts["dataset_raster_size"])

                        ds = import_and_wait(file_path, owner, title=title, timeout=opts["dataset_timeout"])
                        ds.title = title
                        ds.abstract = abstract
                        ds.owner = owner
                        if category:
                            ds.category = category
                        ds.save()
                        resource = ds
                    finally:
                        try:
                            os.remove(file_path)
                        except OSError:
                            pass

            except Exception as exc:
                skipped_counts[rtype] += 1
                self.log("RESOURCES", f"Skipped a {rtype} ({title!r}): {exc}", "WARN")
                continue

            created_counts[rtype] += 1
            resource_rows.append((resource.id, rtype, title, owner.username))
            created_resources.append(resource)

            total_done = sum(created_counts.values())
            if total_done % 100 == 0:
                self.log("RESOURCES", f"...{total_done}/{opts['num_resources']} resources created")

        self.log("RESOURCES", f"Done. Created: {created_counts}. Skipped: {skipped_counts} "
                               f"[{format_duration(time.monotonic() - resources_start)}]")

        # ================= STAGE 3: PERMISSIONS =================
        permissions_start = time.monotonic()
        if opts["permissions_scope"] == "all":
            target_resources = list(ResourceBase.objects.all())
            self.log("PERMISSIONS", f"Scope=all -> {len(target_resources)} resources in the whole instance")
        else:
            target_resources = created_resources
            self.log("PERMISSIONS", f"Scope=created -> {len(target_resources)} resources created in this run")

        if dry_run:
            self.log("PERMISSIONS", "Dry run: skipping actual permission assignment "
                                     "(nothing was persisted in stage 1/2 to attach permissions to).")
            perm_rows = []
        else:
            perm_rows = []
            touched = 0
            for resource in target_resources:
                resource = resource.get_self_resource()
                n_users = random.randint(opts["min_users"], min(opts["max_users"], len(all_users)))
                picked_users = random.sample(all_users, n_users)

                user_perm_spec = {}
                if resource.owner_id:
                    user_perm_spec[resource.owner.username] = LEVELS["manage"]

                for user in picked_users:
                    if resource.owner_id and user.id == resource.owner_id:
                        continue
                    level = random.choice(levels)
                    user_perm_spec[user.username] = LEVELS[level]
                    perm_rows.append((resource.id, resource.title, user.username, level))

                if opts["randomize_anonymous"] and random.choice([True, False]):
                    user_perm_spec["AnonymousUser"] = LEVELS["view"]
                    perm_rows.append((resource.id, resource.title, "AnonymousUser", "view"))

                resource.set_permissions({"users": user_perm_spec, "groups": {}})

                touched += 1
                if touched % 100 == 0:
                    self.log("PERMISSIONS", f"...{touched}/{len(target_resources)} resources given new permissions")

            self.log("PERMISSIONS", f"Done. Resources touched: {touched}. Assignments logged: {len(perm_rows)} "
                                     f"[{format_duration(time.monotonic() - permissions_start)}]")

        # ================= CSV logs =================
        prefix = opts["csv_out_prefix"]

        if user_rows:
            path = f"{prefix}_users.csv"
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["username", "email", "password"])
                w.writerows(user_rows)
            self.log("SUMMARY", f"Wrote {len(user_rows)} user credentials to {path}")

        if resource_rows:
            path = f"{prefix}_resources.csv"
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["resource_id", "resource_type", "title", "owner"])
                w.writerows(resource_rows)
            self.log("SUMMARY", f"Wrote {len(resource_rows)} created resources to {path}")

        if perm_rows:
            path = f"{prefix}_permissions.csv"
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["resource_id", "resource_title", "username", "level"])
                w.writerows(perm_rows)
            self.log("SUMMARY", f"Wrote {len(perm_rows)} permission assignments to {path}")

        # ================= final summary =================
        mode = "DRY RUN — no changes were saved" if dry_run else "changes applied"
        self.log("SUMMARY", "=" * 60)
        self.log("SUMMARY", f"FINISHED ({mode})")
        self.log("SUMMARY", f"  users:       created={len(created_users)} skipped={len(skipped_users)}")
        self.log("SUMMARY", f"  resources:   created={created_counts} skipped={skipped_counts}")
        self.log("SUMMARY", f"  permissions: assignments={len(perm_rows)} "
                             f"(scope={opts['permissions_scope']})")
        self.log("SUMMARY", f"  total duration: {format_duration(time.monotonic() - run_start)}")
        self.log("SUMMARY", "=" * 60)
