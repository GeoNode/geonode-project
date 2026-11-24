from urllib.parse import quote

from django.db.models import Count, Q
from guardian.utils import get_anonymous_user
from django.http import FileResponse, Http404, HttpResponseRedirect
import zipfile

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render

from . import extract, services

from geonode.assets.utils import get_default_asset
from geonode.security.utils import get_visible_resources
from geonode.base.models import ResourceBase

from .models import Emergency, MapFile, MapVersion


def _visible_ids(user):
    """Ids of the resources this user may see (GeoNode's own permission rules)."""
    qs = get_visible_resources(ResourceBase.objects.all(), user, admin_approval_required=False,
                               unpublished_not_visible=False, private_groups_not_visibile=False)
    return qs.values("id")


def catalogue_url_for(keyword_id):
    return f"/catalogue/#/search/?{quote('filter{tkeywords}')}={keyword_id}"


def _median(values):
    values = sorted(values)
    return values[len(values) // 2] if values else None


def emergencies_data(user):
    """One row per emergency with maps this user can see: where (from its maps' extents, else its countries),
    when (first and last map), how many maps, for the map and timeline on the Emergencies page."""
    visible = _visible_ids(user)
    rows = (MapVersion.objects.filter(is_latest=True, resource__in=visible, series__emergency__isnull=False)
            .values_list("series__emergency_id", "map_created", "resource__ll_bbox_polygon"))
    stats = {}
    for em_id, created, poly in rows:
        st = stats.setdefault(em_id, {"count": 0, "dates": [], "x": [], "y": []})
        st["count"] += 1
        if created:
            st["dates"].append(created)
        if poly is not None:
            x0, y0, x1, y1 = poly.extent
            if (x1 - x0) < 60 and (y1 - y0) < 60:  # GeoNode gives maps with no extent the whole world
                st["x"].append((x0 + x1) / 2)
                st["y"].append((y0 + y1) / 2)
    out = []
    for em in Emergency.objects.filter(pk__in=stats).prefetch_related("countries"):
        st = stats[em.pk]
        lon, lat = _median(st["x"]), _median(st["y"])
        if lon is None:
            boxes = [r for r in em.countries.all() if r.bbox_x0 is not None and abs(float(r.bbox_x1) - float(r.bbox_x0)) < 60]
            if boxes:
                lon = sum(float(r.bbox_x0) + float(r.bbox_x1) for r in boxes) / (2 * len(boxes))
                lat = sum(float(r.bbox_y0) + float(r.bbox_y1) for r in boxes) / (2 * len(boxes))
        start = min(st["dates"]) if st["dates"] else None
        year = start.year if start else (int(em.code[:4]) if em.code[:4].isdigit() else None)
        out.append({
            "code": em.code, "title": em.title, "hazard": em.hazard, "image": em.image_url,
            "url": em.get_absolute_url(), "count": st["count"], "current": em.is_current,
            "no_emergency": em.title.endswith(": maps without an emergency"),
            "start": start.date().isoformat() if start else None,
            "end": max(st["dates"]).date().isoformat() if st["dates"] else None,
            "year": year, "lat": lat, "lon": lon,
            "countries": [r.name for r in em.countries.all()],
        })
    out.sort(key=lambda e: (e["start"] or str(e["year"] or 0)), reverse=True)
    return out


def emergency_list(request):
    return render(request, "mapaction/emergency_list.html", {"emergencies": emergencies_data(request.user),
                                                             "can_upload": can_upload(request.user)})


def emergency_detail(request, code):
    em = get_object_or_404(Emergency, code=code)
    visible = _visible_ids(request.user)
    versions = list(MapVersion.objects.filter(series__emergency=em, is_latest=True, resource__in=visible)
                    .select_related("resource", "series").prefetch_related("files")
                    .order_by("-map_created", "series__map_number"))
    # Older versions of each map (visible to this user), newest first, shown as "superseded"
    older = {}
    for o in (MapVersion.objects.filter(series__emergency=em, is_latest=False, resource__in=visible)
              .select_related("resource").order_by("-version")):
        older.setdefault(o.series_id, []).append(o)
    for mv in versions:
        mv.older = older.get(mv.series_id, [])
        files = list(mv.files_for_download())
        mv.primary = (next((f for f in files if f.role == "pdf"), None) or next((f for f in files if f.role == "jpg"), None))
        mv.jpg = next((f for f in files if f.role == "jpg" and f is not mv.primary), None)
        mv.sheets = [f for f in files if f.role == "sheet"]
        mv.others = [f for f in files if f.role in ("zip", "other")]
    return render(request, "mapaction/emergency_detail.html", {
        "emergency": em, "versions": versions, "can_upload": can_upload(request.user),
        "catalogue_url": catalogue_url_for(em.keyword_id) if em.keyword_id else None,
    })


def file_download(request, pk):
    mf = get_object_or_404(MapFile.objects.select_related("version__resource"), pk=pk)
    resource = mf.version.resource
    user = request.user if request.user.is_authenticated else get_anonymous_user()
    if not resource.get_self_resource().user_can(user, "download_resourcebase"):
        raise Http404
    if mf.is_primary:
        # Serve the document's own stored file as itself (GeoNode's /download wraps it in a ZIP)
        asset = get_default_asset(resource)
        location = getattr(asset, "location", None)
        if location:
            return FileResponse(open(location[0], "rb"), as_attachment=True, filename=mf.filename)
        return HttpResponseRedirect(f"/documents/{resource.pk}/download")
    if not mf.file:
        raise Http404
    return FileResponse(mf.file.open("rb"), as_attachment=True, filename=mf.filename)


def can_upload(user):
    return user.is_authenticated and (user.is_staff or user.has_perm("base.add_resourcebase"))


@login_required
def product_upload(request, code=None):
    """Upload a product ZIP from the ArcGIS add-on (or a ZIP of them). "Check only" reports without loading."""
    if not can_upload(request.user):
        raise PermissionDenied
    emergency = get_object_or_404(Emergency, code=code) if code else None
    results, error = [], None
    check_only = True
    if request.method == "POST":
        check_only = bool(request.POST.get("check_only"))
        upload = request.FILES.get("zip")
        if not upload or not upload.name.lower().endswith(".zip"):
            error = "Please choose a product ZIP (.zip)."
        else:
            try:
                for name, members in extract.read_zip_products(upload.name, upload.read()):
                    row = {"name": name}
                    try:
                        p = extract.from_zip(name, members)
                        exists = services.existing_version(p)
                        mv, action = services.publish(p, loaded_by=request.user, dry_run=check_only)
                        if check_only and action == "would load":
                            action = "would replace the existing record" if exists else (
                                "would add a new version" if services.has_series(p) else "would create a new map")
                        row.update(title=p.display_title, action=action, warnings=p.warnings,
                                   emergency=p.emergency_code, sheets=sum(1 for f in p.files if f.role == "sheet"),
                                   files=[f.filename for f in p.files if f.role != "thumbnail"],
                                   public=p.is_public, record=mv.resource_id if mv else None)
                        if emergency and p.emergency_code != emergency.code:
                            row["warnings"] = [f"this ZIP belongs to {p.emergency_code or 'no emergency'}, not {emergency.code}"] + row["warnings"]
                    except Exception as e:  # report per product, keep going
                        row.update(action="error", warnings=[str(e)])
                    results.append(row)
                if not results:
                    error = "No product found: the ZIP has no XML metadata (and no product ZIPs inside)."
            except zipfile.BadZipFile:
                error = "That file is not a valid ZIP."
    return render(request, "mapaction/upload.html", {
        "emergency": emergency, "results": results, "error": error, "check_only": check_only})
