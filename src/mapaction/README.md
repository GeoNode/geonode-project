# mapaction: MapAction's maps on GeoNode

A Django app on top of `kartoza_geonode` (branch `4.4.x-mapaction`, from `4.4.x-geohosting`). It keeps
GeoNode's own models: every map version is a GeoNode **Document** (`ResourceBase`). The app adds the
MapAction structure around it:

| Model | What it is |
|---|---|
| `Emergency` | An operation (CKAN event group), e.g. `2026-npl-001`, with GLIDE, hazard and countries |
| `MapSeries` | One map number in one emergency, e.g. MA027 |
| `MapVersion` | One version of that map; one-to-one with its GeoNode Document; `is_latest` |
| `MapFile` | The files of a version: PDF, JPG, atlas sheets, ZIP, with size and checksum |

Older versions stay reachable by link but are not listed (`advertised=False`); each points to the
newer one with a GeoNode `LinkedResource`.

## What it adds to the site

- `/mapaction/emergencies/`: map and timeline of emergencies, each with its latest maps and downloads
- `/mapaction/emergencies/<code>/upload/` and `/mapaction/upload/`: upload ArcGIS add-on product ZIPs
  (staff or users with `base.add_resourcebase`)
- Catalogue filters for Emergency, Country, Hazard, Theme, Product type, and Language (thesauri + `FACET_PROVIDERS`)
- Map, Downloads, and Versions tabs on the document page (via `_geonode_config.html` and a `mapaction`
  field on the v2 API)
- MapAction header, footer, and colours. The app's `templates/geonode-mapstore-client/` replace the Kartoza
  snippets with the same names (`apps.py` moves this app's templates first), so no Kartoza file is edited.

## Deploying

No new Python packages. After the image is built:

```bash
python manage.py migrate                 # mapaction 0001, 0002
python manage.py mapaction_setup         # thesauri + the "mapaction" service account
python manage.py mapaction_theme         # home-page banner (GeoNode theme)
```

Settings (in `kartoza_geonode/settings.py`, env-overridable): `MAPACTION_SERVICE_USERNAME` (default `mapaction`),
`MAPACTION_CONTACT_EMAIL` (default `geonode@mapaction.org`), `MAPACTION_HIDE_SUPERSEDED` (default `True`).
Map files are stored under `MEDIA_ROOT/mapaction/`.

## Loading data

```bash
python manage.py mapaction_sync_emergencies --mirror /path/to/ckan-mirror
python manage.py mapaction_import_ckan --mirror /path/to/ckan-mirror [--shard 1/4] --apply   # dry run without --apply
python manage.py mapaction_import_zip product.zip [--apply]
python manage.py mapaction_apply_permissions             # Public -> anyone; others -> signed-in users
python manage.py mapaction_purge --emergency <code> [--apply]
```
