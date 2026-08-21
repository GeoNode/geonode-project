"""
Pure-Python(-ish) generators for fake-but-real GIS test data.

No GeoNode imports here on purpose — these functions only touch the
filesystem (via ``tempfile``/``osgeo.gdal``) and stdlib ``json``/``random``,
so they can be unit-tested or reused outside a Django management command.

generate_random_geojson()  -> writes a valid GeoJSON FeatureCollection
generate_random_geotiff()  -> writes a small single-band GeoTIFF via GDAL
"""

import json
import math
import os
import random
import struct

GEOM_TYPES = ["Point", "LineString", "Polygon"]

ATTR_POOL = [
    ("category", lambda rng: rng.choice(["a", "b", "c", "d"])),
    ("value", lambda rng: round(rng.uniform(0, 1000), 2)),
    ("count", lambda rng: rng.randint(0, 500)),
    ("active", lambda rng: rng.choice([True, False])),
    ("label", lambda rng: f"item-{rng.randint(1, 99999)}"),
]


def _random_point(rng, bbox):
    minx, miny, maxx, maxy = bbox
    return [round(rng.uniform(minx, maxx), 6), round(rng.uniform(miny, maxy), 6)]


def _random_linestring(rng, bbox):
    n = rng.randint(2, 6)
    return [_random_point(rng, bbox) for _ in range(n)]


def _random_polygon(rng, bbox):
    # a simple closed ring around a random center — always valid, no self-intersection
    n = rng.randint(4, 10)
    minx, miny, maxx, maxy = bbox
    cx = rng.uniform(minx, maxx)
    cy = rng.uniform(miny, maxy)
    r = rng.uniform(0.01, (min(maxx - minx, maxy - miny) / 4) or 0.5)
    ring = []
    for i in range(n):
        angle = 2 * math.pi * i / n
        wobble = 0.6 + 0.4 * rng.random()
        ring.append([round(cx + r * wobble * math.cos(angle), 6),
                     round(cy + r * wobble * math.sin(angle), 6)])
    ring.append(ring[0])  # close the ring
    return [ring]


def _random_feature(rng, bbox, geom_type):
    if geom_type == "Point":
        geometry = {"type": "Point", "coordinates": _random_point(rng, bbox)}
    elif geom_type == "LineString":
        geometry = {"type": "LineString", "coordinates": _random_linestring(rng, bbox)}
    else:
        geometry = {"type": "Polygon", "coordinates": _random_polygon(rng, bbox)}

    n_attrs = rng.randint(1, len(ATTR_POOL))
    properties = {name: gen(rng) for name, gen in rng.sample(ATTR_POOL, n_attrs)}

    return {"type": "Feature", "geometry": geometry, "properties": properties}


def generate_random_geojson(
    out_path,
    min_features=10,
    max_features=5000,
    bbox=(-180.0, -85.0, 180.0, 85.0),
    geom_type=None,
    seed=None,
):
    """
    Write a random valid GeoJSON FeatureCollection to ``out_path``.

    All features in one file share the same geometry type — GeoServer/OGR
    import a single-geometry-type layer far more reliably than a mixed one.
    ``geom_type`` forces a specific type (Point/LineString/Polygon);
    otherwise one is picked at random per call (still uniform per file).

    Returns (out_path, feature_count, geom_type).
    """
    rng = random.Random(seed) if seed is not None else random
    n_features = rng.randint(min_features, max_features)
    chosen_type = geom_type or rng.choice(GEOM_TYPES)

    features = [_random_feature(rng, bbox, chosen_type) for _ in range(n_features)]
    fc = {"type": "FeatureCollection", "features": features}

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(fc, f)

    return out_path, n_features, chosen_type


def generate_random_geotiff(out_path, width=32, height=32, seed=None):
    """
    Write a small single-band Float32 GeoTIFF with random values, a real
    CRS (EPSG:4326) and a real geotransform, using GDAL's Python bindings
    (already a GeoNode dependency — no extra requirement added).

    Kept deliberately tiny (default 32x32) so generation + upload stays
    fast and disk-cheap even for thousands of rasters.

    Returns (out_path, width, height).
    """
    from osgeo import gdal, osr

    rng = random.Random(seed) if seed is not None else random

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    driver = gdal.GetDriverByName("GTiff")
    dataset = driver.Create(out_path, width, height, 1, gdal.GDT_Float32)

    # arbitrary small extent somewhere on the globe, north-up, square pixels
    origin_x = rng.uniform(-170, 160)
    origin_y = rng.uniform(-80, 80)
    pixel_size = rng.uniform(0.001, 0.01)
    dataset.SetGeoTransform((origin_x, pixel_size, 0, origin_y, 0, -pixel_size))

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    dataset.SetProjection(srs.ExportToWkt())

    band = dataset.GetRasterBand(1)
    row_fmt = f"<{width}f"
    for y in range(height):
        row = [rng.uniform(0, 1000) for _ in range(width)]
        band.WriteRaster(0, y, width, 1, struct.pack(row_fmt, *row))

    band.FlushCache()
    dataset.FlushCache()
    dataset = None  # noqa: F841 -- dereferencing closes/flushes the file (GDAL idiom)

    return out_path, width, height
