from django.contrib import admin
from django.utils.html import format_html

from .models import Emergency, MapFile, MapSeries, MapVersion


class MapFileInline(admin.TabularInline):
    model = MapFile
    extra = 0
    fields = ("order", "role", "label", "filename", "is_primary", "size", "file")
    readonly_fields = ("size",)


class MapVersionInline(admin.TabularInline):
    model = MapVersion
    extra = 0
    fields = ("version", "is_latest", "record", "product_type", "map_created", "source", "loaded_by", "loaded_at")
    readonly_fields = ("record", "is_latest", "loaded_by", "loaded_at")
    show_change_link = True

    @admin.display(description="GeoNode record")
    def record(self, obj):
        return format_html('<a href="/catalogue/#/document/{}">{}</a>', obj.resource_id, obj.resource.title)


@admin.register(Emergency)
class EmergencyAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "hazard", "glide", "is_current", "short_label")
    list_editable = ("is_current", "short_label")
    search_fields = ("code", "title", "glide")
    list_filter = ("hazard",)
    filter_horizontal = ("countries",)


@admin.register(MapSeries)
class MapSeriesAdmin(admin.ModelAdmin):
    list_display = ("map_number", "emergency", "version_count")
    search_fields = ("map_number", "emergency__code", "emergency__title")
    inlines = [MapVersionInline]

    @admin.display(description="Versions")
    def version_count(self, obj):
        return obj.versions.count()


@admin.register(MapVersion)
class MapVersionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "is_latest", "product_type", "map_created", "source", "loaded_by", "loaded_at")
    list_filter = ("is_latest", "product_type", "source")
    search_fields = ("series__map_number", "series__emergency__code", "resource__title", "source_id")
    readonly_fields = ("loaded_by", "loaded_at")
    inlines = [MapFileInline]
