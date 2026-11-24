"""Publish a Product as MapAction map version, applying the rules agreed with MapAction (17 Nov 2026):

- a map marked Public is open to anyone; anything else is for signed-in users only
- the same emergency + map number + version replaces the record (only records this code created)
- a new version gets its own record, linked to the one before; older versions stay retrievable but unlisted
- the JPG and atlas sheets are downloads of the same record ("available for download as a link from the item")
- geonode@mapaction.org is the contact; who ran the load is kept for staff only
"""
import hashlib
import logging
import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files import File
from django.db import transaction
from django.utils.timezone import now

from geonode.assets.utils import create_asset_and_link
from geonode.base.models import LinkedResource, Region, ResourceBase, Thesaurus, ThesaurusKeyword, ThesaurusKeywordLabel
from geonode.documents.models import Document
from geonode.resource.manager import resource_manager
from geonode.resource.utils import resourcebase_post_save

from . import vocab
from .extract import Product
from .models import Emergency, MapFile, MapSeries, MapVersion

log = logging.getLogger(__name__)

SERVICE_USERNAME = getattr(settings, "MAPACTION_SERVICE_USERNAME", "mapaction")
SERVICE_EMAIL = getattr(settings, "MAPACTION_CONTACT_EMAIL", "geonode@mapaction.org")
HIDE_SUPERSEDED = getattr(settings, "MAPACTION_HIDE_SUPERSEDED", True)

THESAURI = {
    # identifier: (title, order)  -- order places them in the catalogue's filter panel
    "mapaction-emergency": ("Emergency", 1),
    "mapaction-hazard": ("Hazard type", 3),
    "mapaction-theme": ("Theme", 4),
    "mapaction-product-type": ("Product type", 5),
    "mapaction-language": ("Language", 6),
}


# ---------------------------------------------------------------- vocabularies

def thesaurus(identifier):
    title, order = THESAURI[identifier]
    t, _ = Thesaurus.objects.get_or_create(identifier=identifier, defaults={
        "title": title, "description": f"MapAction {title}", "facet": True, "order": order, "card_min": 0, "card_max": -1})
    return t


def term(identifier, key, label):
    """A ThesaurusKeyword (the filter value) with its English label."""
    kw, _ = ThesaurusKeyword.objects.get_or_create(thesaurus=thesaurus(identifier), alt_label=key)
    ThesaurusKeywordLabel.objects.update_or_create(keyword=kw, lang="en", defaults={"label": label})
    return kw


def setup_vocabularies():
    for t in vocab.THEMES:
        term("mapaction-theme", t, t)
    for k, v in vocab.PRODUCT_TYPES.items():
        term("mapaction-product-type", k, v)
    for k, v in vocab.LANGUAGES.items():
        term("mapaction-language", k, v)
    for v in sorted(set(vocab.HAZARDS.values())):
        term("mapaction-hazard", v, v)
    return {i: thesaurus(i) for i in THESAURI}


# ---------------------------------------------------------------- accounts and permissions

def service_account():
    User = get_user_model()
    user, created = User.objects.get_or_create(username=SERVICE_USERNAME, defaults={
        "email": SERVICE_EMAIL, "first_name": "MapAction", "last_name": "", "is_active": True})
    if created:
        user.set_unusable_password()
        user.save()
    return user


VIEW_AND_DOWNLOAD = ["view_resourcebase", "download_resourcebase"]


def permission_spec(resource, is_public):
    """Agreed rule: Public -> anyone may view and download; anything else -> signed-in users only.
    GeoNode's expanded form (names, not ids), keeping the owner's and managers' existing rights."""
    from guardian.utils import get_anonymous_user

    info = resource.get_self_resource().get_all_level_info()
    anonymous = get_anonymous_user()
    users = {u.username: sorted(p) for u, p in info.get("users", {}).items() if u != anonymous}
    groups = {"registered-members": VIEW_AND_DOWNLOAD}
    if is_public:
        groups["anonymous"] = VIEW_AND_DOWNLOAD
    return {"users": users, "groups": groups}


def apply_permissions(resource, is_public):
    resource_manager.set_permissions(None, instance=resource, permissions=permission_spec(resource, is_public))


# ---------------------------------------------------------------- emergencies and regions

def regions_for(product: Product):
    found = []
    for name in product.countries:
        r = Region.objects.filter(name__iexact=name).first()
        if not r and "(" in name:  # "Venezuela (Bolivarian Republic of)" -> "Venezuela"
            r = Region.objects.filter(name__iexact=name.split("(")[0].strip()).first()
        if r:
            found.append(r)
    if not found and product.country_iso3:
        r = Region.objects.filter(code=product.country_iso3).first()
        if r:
            found.append(r)
    if product.countries and not found:
        product.warnings.append(f"country not matched to a GeoNode region: {', '.join(product.countries)}")
    return found


def get_emergency(product: Product, regions):
    if not product.emergency_code:
        return None
    em, _ = Emergency.objects.get_or_create(code=product.emergency_code, defaults={"title": product.emergency_title or product.emergency_code})
    changed = False
    for attr, value in (("title", product.emergency_title), ("description", product.emergency_description),
                        ("image_url", product.emergency_image), ("glide", product.glide)):
        if value and not getattr(em, attr):
            setattr(em, attr, value)
            changed = True
    if not em.hazard and em.glide:
        em.hazard, changed = vocab.hazard(em.glide), True
    if not em.source_url and product.source == "ckan":
        em.source_url, changed = f"https://maps.mapaction.org/event/{em.code}", True
    if not em.keyword_id:
        em.keyword, changed = term("mapaction-emergency", em.code, em.title), True
    if changed:
        em.save()
    if regions:
        em.countries.add(*regions)
    return em


# ---------------------------------------------------------------- files

def _materialise(f, workdir: Path) -> Path | None:
    """A local path for a ProductFile (ZIP members are written out to a temp dir)."""
    if f.path and Path(f.path).exists():
        return Path(f.path)
    if f.data is not None:
        p = workdir / f.filename
        p.write_bytes(f.data)
        return p
    return None


def _sha256(path: Path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- publish

def describe(doc: Document, product: Product, emergency, regions, owner):
    doc.title = product.display_title[:255]
    doc.abstract = product.summary or product.title
    doc.date = product.created or now()
    doc.date_type = "creation"
    if product.languages:
        doc.language = product.languages[0]
    doc.attribution = product.datasource[:2048] if product.datasource else None
    public_details = [("Scale", product.scale), ("Paper size", product.papersize), ("Location", product.location),
                      ("Donor", product.donor)]
    doc.supplemental_information = "; ".join(f"{k}: {v}" for k, v in public_details if v) or None
    doc.metadata_author = owner
    doc.poc = owner
    doc.advertised = True
    if product.bbox:
        doc.set_bbox_polygon(product.bbox, "EPSG:4326")
    doc.save()
    doc.regions.set(regions)
    kws = []
    if emergency and emergency.keyword_id:
        kws.append(emergency.keyword)
    if emergency and emergency.hazard:
        kws.append(term("mapaction-hazard", emergency.hazard, emergency.hazard))
    for t in product.themes:
        kws.append(term("mapaction-theme", t, t))
    if product.product_type:
        kws.append(term("mapaction-product-type", product.product_type, vocab.PRODUCT_TYPES[product.product_type]))
    for code in product.languages:
        kws.append(term("mapaction-language", code, vocab.LANGUAGES.get(code, code)))
    doc.tkeywords.set(kws)
    # GeoNode free-text keywords: the map number helps people who know it ("MA004")
    if product.map_number.upper().startswith("MA"):
        doc.keywords.add(product.map_number.upper())


def _series_filter(product: Product):
    return {"emergency__code": product.emergency_code or None, "map_number": product.map_number} if product.emergency_code \
        else {"emergency__isnull": True, "map_number": product.map_number}


def has_series(product: Product):
    return MapSeries.objects.filter(**_series_filter(product)).exists()


def existing_version(product: Product):
    return MapVersion.objects.filter(**{f"series__{k}": v for k, v in _series_filter(product).items()},
                                     version=product.version).first()


def publish(product: Product, loaded_by=None, dry_run=False):
    """Create or replace one map version. Returns (MapVersion | None, action)."""
    primary = next((f for f in product.files if f.role == "pdf"), None) or next((f for f in product.files if f.role == "jpg"), None)
    if not primary:
        return None, "skip: no PDF or JPG"
    if dry_run:
        return None, "would load"

    owner = service_account()
    regions = regions_for(product)
    workdir = Path(tempfile.mkdtemp(prefix="mapaction-"))
    try:
        with transaction.atomic():
            emergency = get_emergency(product, regions)
            series, _ = MapSeries.objects.get_or_create(emergency=emergency, map_number=product.map_number)
            existing = MapVersion.objects.filter(series=series, version=product.version).select_related("resource").first()
            action = "replaced" if existing else "created"
            primary_path = _materialise(primary, workdir)
            if not primary_path:
                return None, f"skip: {primary.filename} not available locally"

            if existing:
                # Same emergency + map number + version: replace in place (the record's URL stays the same)
                doc = existing.resource.get_real_instance()
                old_primary = existing.files.filter(is_primary=True).first()
                if not old_primary or old_primary.sha256 != _sha256(primary_path):
                    for link in doc.link_set.filter(asset__isnull=False):
                        link.asset.delete() if link.asset else None
                    create_asset_and_link(doc, owner, [str(primary_path)], clone_files=True)
                    doc.extension = primary_path.suffix.lstrip(".").lower()
                existing.files.all().delete()
                mv = existing
            else:
                doc = Document.objects.create(owner=owner, title=product.display_title[:255], resource_type="document",
                                              extension=primary_path.suffix.lstrip(".").lower(), abstract=product.summary or "")
                create_asset_and_link(doc, owner, [str(primary_path)], clone_files=True)
                mv = MapVersion(series=series, version=product.version, resource=doc.resourcebase_ptr)

            describe(doc, product, emergency, regions, owner)
            mv.product_type = product.product_type
            mv.map_created = product.created
            mv.metadata = product.metadata
            mv.source, mv.source_id, mv.source_url = product.source, product.source_id, product.source_url
            mv.loaded_by = loaded_by
            mv.save()

            for order, f in enumerate(product.files):
                if f.role == "thumbnail":
                    continue  # GeoNode makes a sharper one from the PDF
                path = primary_path if f is primary else _materialise(f, workdir)
                if not path:
                    product.warnings.append(f"{f.filename}: not available locally")
                    continue
                mf = MapFile(version=mv, role=f.role, label=f.label, filename=f.filename, is_primary=f is primary,
                             size=path.stat().st_size, sha256=_sha256(path), order=order, source_url=f.url)
                if f is not primary:
                    with open(path, "rb") as fh:
                        mf.file.save(f"{series.pk}-{product.version}-{f.filename}", File(fh), save=False)
                mf.save()

        # Outside the transaction, as GeoNode's own document API does
        doc.set_missing_info()
        resourcebase_post_save(doc.get_real_instance())
        resource_manager.set_permissions(None, instance=doc, permissions=None, created=True)  # owner and defaults first
        apply_permissions(doc, product.is_public)
        resource_manager.set_thumbnail(doc.uuid, instance=doc, overwrite=False)
        refresh_series(series)
        return mv, action
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def refresh_series(series: MapSeries):
    """Latest version listed; older ones unlisted but reachable; each version linked to the one before."""
    versions = list(series.versions.order_by("version").select_related("resource"))
    if not versions:
        return
    latest = versions[-1]
    for v in versions:
        is_latest = v.pk == latest.pk
        if v.is_latest != is_latest:
            MapVersion.objects.filter(pk=v.pk).update(is_latest=is_latest)
        ResourceBase.objects.filter(pk=v.resource_id).update(advertised=is_latest or not HIDE_SUPERSEDED)
    for older, newer in zip(versions, versions[1:]):
        LinkedResource.objects.get_or_create(source=newer.resource, target=older.resource, defaults={"internal": False})
