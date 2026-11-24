"""MapAction's own model of a map product, layered on GeoNode.

    Emergency ──< MapSeries ──< MapVersion ──1:1── GeoNode Document (a ResourceBase)
                                    └──< MapFile (PDF, JPG, atlas sheets, ZIP…)

Every listed record in GeoNode is still a plain Document, so permissions, search, filters, thumbnails,
ISO/CSW and the REST API keep working. These tables add what GeoNode has no notion of: the map
across its versions, which version is current, and the set of files that make up one version.
"""
from django.conf import settings
from django.db import models
from django.urls import reverse

from geonode.base.models import ResourceBase, Region, ThesaurusKeyword


class Emergency(models.Model):
    """An operation/deployment: CKAN's "event" group, the XML's operationID."""

    code = models.CharField(max_length=64, unique=True, help_text="e.g. 2026-mdg-001 (legacy: 00217, maria)")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    glide = models.CharField("GLIDE number", max_length=64, blank=True, help_text="Staff only")
    hazard = models.CharField(max_length=64, blank=True, help_text="Derived from the GLIDE prefix")
    countries = models.ManyToManyField(Region, blank=True, related_name="mapaction_emergencies")
    image_url = models.URLField(max_length=500, blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    keyword = models.ForeignKey(ThesaurusKeyword, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="+", help_text="The Emergency filter term")
    is_current = models.BooleanField("current", default=False,
                                     help_text="Shown in the red 'Latest maps and data' bar at the top of every page")
    short_label = models.CharField(max_length=80, blank=True, help_text="For that bar, e.g. 'Flash Flood: Nepal'")

    class Meta:
        ordering = ("-code",)
        verbose_name_plural = "emergencies"

    def __str__(self):
        return f"{self.title} ({self.code})"

    def get_absolute_url(self):
        return reverse("mapaction:emergency", args=[self.code])


class MapSeries(models.Model):
    """One map across all its versions: emergency + map number (e.g. 2026-mdg-001 / MA004)."""

    emergency = models.ForeignKey(Emergency, null=True, blank=True, on_delete=models.PROTECT, related_name="series")
    map_number = models.CharField(max_length=128, help_text="MA004; legacy records keep their CKAN reference")

    class Meta:
        unique_together = (("emergency", "map_number"),)
        ordering = ("emergency__code", "map_number")
        verbose_name_plural = "map series"

    def __str__(self):
        return f"{self.emergency.code if self.emergency else '-'} / {self.map_number}"

    @property
    def latest(self):
        return self.versions.filter(is_latest=True).first()


class MapVersion(models.Model):
    """One version of a map. It *is* one GeoNode Document; this row adds MapAction's own facts."""

    SOURCES = (("ckan", "CKAN migration"), ("zip", "Product ZIP"), ("api", "API"), ("manual", "Manual"))
    PRODUCT_TYPES = (("mapsheet", "Map sheet"), ("atlas", "Atlas"), ("mapbook", "Map book"), ("mapseries", "Map series"))

    series = models.ForeignKey(MapSeries, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    resource = models.OneToOneField(ResourceBase, on_delete=models.CASCADE, related_name="mapaction_version")
    is_latest = models.BooleanField(default=True, db_index=True)
    product_type = models.CharField(max_length=32, blank=True, choices=PRODUCT_TYPES)
    map_created = models.DateTimeField(null=True, blank=True, help_text="From the XML createdate/createtime/timezone")
    metadata = models.JSONField(default=dict, blank=True, help_text="Every source field, as received (schema will change)")
    source = models.CharField(max_length=16, choices=SOURCES)
    source_id = models.CharField(max_length=255, blank=True, help_text="CKAN package name, ZIP name…")
    source_url = models.URLField(max_length=500, blank=True)
    loaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name="+", help_text="Staff only: who ran the load")
    loaded_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("series", "version"),)
        ordering = ("series", "-version")

    def __str__(self):
        return f"{self.series} v{self.version:02d}"

    @property
    def label(self):
        return f"v{self.version:02d}"

    def files_for_download(self):
        return self.files.exclude(role=MapFile.THUMBNAIL).order_by("order", "id")


class MapFile(models.Model):
    """A file of one map version. The primary file is the Document's own; the others are stored here."""

    PDF, JPG, SHEET, ZIP, THUMBNAIL, OTHER = "pdf", "jpg", "sheet", "zip", "thumbnail", "other"
    ROLES = ((PDF, "PDF"), (JPG, "JPG"), (SHEET, "Atlas sheet"), (ZIP, "ZIP"), (THUMBNAIL, "Thumbnail"), (OTHER, "Other"))

    version = models.ForeignKey(MapVersion, on_delete=models.CASCADE, related_name="files")
    role = models.CharField(max_length=16, choices=ROLES)
    label = models.CharField(max_length=255, help_text="What a visitor sees, e.g. 'PDF', 'Gaza (MZ02)'")
    is_primary = models.BooleanField(default=False, help_text="The Document's own file (not stored twice)")
    file = models.FileField(upload_to="mapaction/%Y/%m/", max_length=500, blank=True)
    filename = models.CharField(max_length=255)
    size = models.BigIntegerField(null=True, blank=True)
    sha256 = models.CharField(max_length=64, blank=True)
    order = models.PositiveIntegerField(default=0)
    source_url = models.URLField(max_length=500, blank=True)

    class Meta:
        ordering = ("version", "order", "id")

    def __str__(self):
        return f"{self.version}: {self.label}"

    def get_download_url(self):
        return reverse("mapaction:file-download", args=[self.pk])
