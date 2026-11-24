"""Expose MapAction's model inside GeoNode's own resource API (/api/v2/resources/<pk>, /api/v2/documents/<pk>).

The GeoNode client's detail panel reads that JSON, so with a `mapaction` block there it can show the
map's emergency, map number, version, downloads and versions without rebuilding the client.
"""
from django.urls import reverse
from django.utils.html import escape
from dynamic_rest.fields.fields import DynamicComputedField

from . import vocab


def mapaction_info(resource, request=None):
    mv = getattr(resource, "mapaction_version", None)
    if mv is None:
        return None
    series, em = mv.series, mv.series.emergency
    build = request.build_absolute_uri if request else (lambda u: u)
    latest_row = series.versions.filter(is_latest=True).first()
    latest_label = latest_row.label if latest_row else ""
    files = []
    for f in mv.files_for_download():
        title = f"{f.label}" + (f" ({_size(f.size)})" if f.size else "")
        if not mv.is_latest and latest_label:
            title += f": superseded by {latest_label}"
        item = {"title": title, "role": f.role,
                "download_url": build(reverse("mapaction:file-download", args=[f.pk]))}
        item["extras"] = {"content": {"title": item["title"], "download_url": item["download_url"]}}  # client's assets tab
        files.append(item)
    languages = ", ".join(vocab.LANGUAGES.get(k.alt_label, k.alt_label)
                          for k in resource.tkeywords.filter(thesaurus__identifier="mapaction-language"))
    versions = [{"pk": v.resource_id, "version": v.version, "label": v.label, "is_latest": v.is_latest,
                 "date": v.map_created.isoformat() if v.map_created else None,
                 "detail_url": f"/catalogue/#/document/{v.resource_id}"}
                for v in series.versions.order_by("-version")]
    latest = next((v for v in versions if v["is_latest"]), None)
    rows = []
    for v in series.versions.order_by("-version").select_related("resource"):
        when = v.map_created.strftime("%-d %b %Y %H:%M") if v.map_created else ""
        tag = " (latest)" if v.is_latest else ""
        text = f"{v.label}{tag}{' · ' + when if when else ''}: {escape(v.resource.title.split(': ', 1)[-1])}"
        rows.append(f"<li><strong>{text}</strong> (this version)</li>" if v.pk == mv.pk
                    else f'<li><a href="/catalogue/#/document/{v.resource_id}">{text}</a></li>')
    versions_html = f'<ol style="padding-left:18px;margin:0">{"".join(rows)}</ol>' 
    themes = [k.alt_label for k in resource.tkeywords.filter(thesaurus__identifier="mapaction-theme")]
    return {
        "map_number": series.map_number,
        "version": mv.version,
        "version_label": mv.label + (" (latest)" if mv.is_latest else f" (superseded by {latest['label']})" if latest else ""),
        "is_latest": mv.is_latest,
        "latest_url": latest["detail_url"] if latest and not mv.is_latest else None,
        "product_type": vocab.PRODUCT_TYPES.get(mv.product_type, ""),
        "themes": ", ".join(themes),
        "languages": languages,
        "emergency": {"code": em.code, "title": em.title, "hazard": em.hazard,
                      "url": reverse("mapaction:emergency", args=[em.code])} if em else None,
        "files": files,
        "versions": versions,
        "versions_html": versions_html,
        "version_count": len(versions),
        "source_url": mv.source_url,
    }


def _size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024


class MapActionField(DynamicComputedField):
    def __init__(self, **kwargs):
        kwargs.setdefault("read_only", True)
        super().__init__(**kwargs)

    def get_attribute(self, instance):
        try:
            return mapaction_info(instance, self.context.get("request"))
        except Exception:  # never break GeoNode's API because of our extra block
            return None

    def to_representation(self, value):
        return value


def install():
    """Add the field to GeoNode's serializers and to the client's API presets."""
    from django.conf import settings
    from geonode.base.api.serializers import ResourceBaseSerializer
    from geonode.documents.api.serializers import DocumentSerializer

    for serializer in (ResourceBaseSerializer, DocumentSerializer):
        serializer._declared_fields["mapaction"] = MapActionField()
        fields = serializer.Meta.fields
        if "mapaction" not in fields:
            serializer.Meta.fields = (list(fields) if isinstance(fields, list) else tuple(fields)) + (
                ["mapaction"] if isinstance(fields, list) else ("mapaction",))
    for preset in ("viewer_common", "catalog_list", "document_list"):
        p = settings.REST_API_PRESETS.get(preset)
        if p and "mapaction" not in p.get("include[]", []):
            p.setdefault("include[]", []).append("mapaction")
