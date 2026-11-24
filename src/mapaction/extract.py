"""Turn a CKAN package (mirror) or a product ZIP's <mapdoc> XML into one clean Product.

Both sources carry the same field names (the ArcGIS add-on's XML is what CKAN stored as extras), so both
end up in the same shape and go through the same publish code.
Extent handling follows the existing loader (other/loader/load_products.py).
"""
import datetime as dt
import io
import math
import zipfile
import pathlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from . import vocab

SHEET_RE = re.compile(r"-mapbook-(?P<label>.+?)-\d+dpi\.pdf$", re.I)


@dataclass
class ProductFile:
    role: str  # pdf | jpg | sheet | zip | thumbnail | other
    label: str
    filename: str
    path: pathlib.Path | None = None  # local file, when we have it
    url: str = ""  # where it came from
    data: bytes | None = None  # in-memory (ZIP members)


@dataclass
class Product:
    source: str
    source_id: str
    source_url: str = ""
    emergency_code: str = ""
    emergency_title: str = ""
    emergency_description: str = ""
    emergency_image: str = ""
    map_number: str = ""
    version: int = 1
    title: str = ""
    summary: str = ""
    countries: list = field(default_factory=list)  # names as given
    country_iso3: str = ""  # from the emergency code, e.g. 2026-mdg-001 -> MDG
    location: str = ""
    themes: list = field(default_factory=list)
    product_type: str = ""
    languages: list = field(default_factory=list)  # ISO 639-2
    glide: str = ""
    created: dt.datetime | None = None
    bbox: list | None = None  # [minx, miny, maxx, maxy] EPSG:4326
    is_public: bool = False
    scale: str = ""
    papersize: str = ""
    datasource: str = ""
    donor: str = ""
    files: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)  # all source fields as received
    warnings: list = field(default_factory=list)

    @property
    def display_title(self):
        if self.map_number and re.match(r"^MA\d+", self.map_number, re.I):
            return f"{self.map_number.upper()} v{self.version:02d}: {self.title}"
        return self.title


# ---------------------------------------------------------------- extent

def utm_to_lonlat(e, n, zone, north):
    """Inverse transverse Mercator on WGS 84 (Snyder 1987), as in the existing loader."""
    a, f, k0 = 6378137.0, 1 / 298.257223563, 0.9996
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    x = e - 500000.0
    y = n if north else n - 1e7
    mu = (y / k0) / (a * (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    phi = (mu + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu) + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
           + (151 * e1**3 / 96) * math.sin(6 * mu) + (1097 * e1**4 / 512) * math.sin(8 * mu))
    s, c, t_ = math.sin(phi), math.cos(phi), math.tan(phi)
    N = a / math.sqrt(1 - e2 * s**2)
    T, C = t_**2, ep2 * c**2
    R = a * (1 - e2) / (1 - e2 * s**2) ** 1.5
    D = x / (N * k0)
    lat = phi - (N * t_ / R) * (D**2 / 2 - (5 + 3 * T + 10 * C - 4 * C**2 - 9 * ep2) * D**4 / 24
                                + (61 + 90 * T + 298 * C + 45 * T**2 - 252 * ep2 - 3 * C**2) * D**6 / 720)
    lon = (D - (1 + 2 * T + C) * D**3 / 6 + (5 - 2 * C + 28 * T - 3 * C**2 + 8 * ep2 + 24 * T**2) * D**5 / 120) / c
    return math.degrees(lon) + (zone * 6 - 183), math.degrees(lat)


def extent(md):
    """[minx, miny, maxx, maxy] in degrees, or None (with a reason) when it cannot be trusted."""
    try:
        x0, x1, y0, y1 = (float(str(md[k]).replace(",", "")) for k in ("xmin", "xmax", "ymin", "ymax"))
    except (KeyError, ValueError, TypeError):
        return None, "no extent"
    if x0 >= x1 or y0 >= y1:
        return None, "empty extent"
    proj = vocab.clean(md.get("proj"))
    m = re.search(r"UTM[_ ]Zone[_ ](\d+)\s*([NS])", proj, re.I) or re.search(r"UTM\s*(\d+)\s*([NS])", proj, re.I)
    if m:
        pts = [utm_to_lonlat(x, y, int(m[1]), m[2].upper() == "N") for x in (x0, x1) for y in (y0, y1)]
        lons, lats = zip(*pts)
        x0, x1, y0, y1 = min(lons), max(lons), min(lats), max(lats)
    elif not (abs(x0) <= 180 and abs(x1) <= 180 and abs(y0) <= 90 and abs(y1) <= 90):
        return None, f"projection not understood: {proj or 'empty'}"
    if not (-180 <= x0 and x1 <= 180 and -90 <= y0 and y1 <= 90):
        return None, "extent outside the world"
    return [round(v, 5) for v in (x0, y0, x1, y1)], ""


# ---------------------------------------------------------------- dates

def created_at(md):
    d, t, tz = vocab.clean(md.get("createdate")), vocab.clean(md.get("createtime")), vocab.clean(md.get("timezone"))
    if not d:
        return None
    d = d.split(" ")[0] if re.match(r"^\d{4}-\d{2}-\d{2} ", d) else d
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M", "%Y/%m/%d"):
        try:
            day = dt.datetime.strptime(d, fmt)
            break
        except ValueError:
            continue
    else:
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})", t)
    if m:
        day = day.replace(hour=int(m[1]), minute=int(m[2]))
    offset = dt.timezone.utc
    m = re.match(r"^UTC\s*([+-])(\d{1,2}):?(\d{2})?$", tz)
    if m:
        delta = dt.timedelta(hours=int(m[2]), minutes=int(m[3] or 0))
        offset = dt.timezone(delta if m[1] == "+" else -delta)
    return day.replace(tzinfo=offset)


# ---------------------------------------------------------------- files

def classify(filename, primary_pdf=""):
    name = filename.lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if name == "thumbnail.png":
        return "thumbnail", "Thumbnail"
    if ext == "pdf":
        m = SHEET_RE.search(filename)
        if m and filename != primary_pdf:
            return "sheet", m.group("label").replace("_", " ").strip()
        return "pdf", "PDF"
    if ext in ("jpg", "jpeg"):
        return "jpg", "JPG"
    if ext == "zip":
        return "zip", "ZIP package"
    if ext in ("png", "gif") and "thumb" in name:
        return "thumbnail", "Thumbnail"
    return "other", filename


def order_files(files):
    """PDF first, then JPG, then atlas sheets A-Z, then the rest. Exactly one primary candidate first."""
    rank = {"pdf": 0, "jpg": 1, "sheet": 2, "zip": 3, "other": 4, "thumbnail": 5}
    files.sort(key=lambda f: (rank.get(f.role, 9), f.label.lower()))
    pdfs = [f for f in files if f.role == "pdf"]
    for extra in pdfs[1:]:  # several un-patterned PDFs: keep the first as "PDF", label the others by file name
        extra.role, extra.label = "sheet", pathlib.Path(extra.filename).stem
    files.sort(key=lambda f: (rank.get(f.role, 9), f.label.lower()))
    return files


# ---------------------------------------------------------------- common

def _fill(p: Product, md: dict, filenames=()):
    p.metadata = md
    p.map_number = vocab.clean(md.get("mapNumber")).upper()
    p.title = vocab.clean(md.get("title")) or p.title
    p.summary = vocab.clean(md.get("summary")) or p.summary
    p.countries = [c for c in [vocab.clean(md.get("countries"))] if c]
    p.location = vocab.clean(md.get("location"))
    p.languages = vocab.languages(md.get("language-iso2") or md.get("language_iso2"), md.get("language"))
    p.glide = vocab.glide(md.get("glideno") or md.get("glidenumber") or md.get("Glide") or md.get("glide-num"))
    p.created = created_at(md)
    p.bbox, why = extent(md)
    if why:
        p.warnings.append(why)
    p.is_public = vocab.access_is_public(md.get("access"))
    if not p.is_public:
        p.warnings.append(f"access is {vocab.clean(md.get('access')) or 'empty'}: signed-in users only")
    p.scale = vocab.clean(md.get("scale"))
    p.papersize = vocab.clean(md.get("papersize"))
    p.datasource = vocab.clean(md.get("datasource")).rstrip(" ,")
    p.donor = vocab.clean(md.get("donor"))
    p.product_type = vocab.product_type(md.get("product-type"), filenames)
    if p.emergency_code and re.match(r"^\d{4}-[a-z]{3}-\d{2,3}$", p.emergency_code):
        p.country_iso3 = p.emergency_code.split("-")[1].upper()
    if p.title.endswith(":"):
        p.title = p.title.rstrip(" :")
        p.warnings.append("title ended with ':'")
    return p


def _norm_extras(extras):
    """CKAN extras list -> dict, with keys trimmed (some carry trailing tabs)."""
    out = {}
    for e in extras or []:
        k = str(e.get("key", "")).strip()
        if k and k not in out:
            out[k] = e.get("value")
    return out


def from_ckan(pkg: dict, mirror_root: pathlib.Path) -> Product:
    md = _norm_extras(pkg.get("extras"))
    events = [g for g in pkg.get("groups") or [] if g.get("type") == "event"]
    ev = events[0] if events else {}
    p = Product(source="ckan", source_id=pkg["name"], source_url=f"https://maps.mapaction.org/dataset/{pkg['name']}",
                emergency_code=ev.get("name", ""), emergency_title=(ev.get("title") or ev.get("display_name") or "").strip(),
                emergency_description=ev.get("description", ""), emergency_image=ev.get("image_display_url", ""),
                title=(pkg.get("title") or "").strip(), summary=(pkg.get("notes") or "").strip())
    if len(events) > 1:
        p.warnings.append(f"{len(events)} emergencies; using {ev.get('name')}")
    if not events:
        # ~140 records (country map packs, remote mapping…) have no emergency. Group them by the scope in their
        # CKAN name ("bdi-ma001-v1" -> "bdi"), titled from their location group, so map numbers don't collide.
        m = re.match(r"^(?P<scope>.+?)-ma\d+", pkg["name"], re.I)
        place = next((g for g in pkg.get("groups") or [] if g.get("type") == "location"), {})
        p.emergency_code = (m.group("scope") if m else pkg["name"])[:64]
        p.emergency_title = f"{(place.get('title') or p.emergency_code).strip()}: maps without an emergency"
        p.warnings.append(f"no emergency in CKAN; grouped as {p.emergency_code}")
    try:
        p.version = int(pkg.get("version") or md.get("versionNumber") or re.search(r"-v(\d+)$", pkg["name"])[1])
    except (TypeError, ValueError):
        p.version = 1
    p.themes = [t for t in pkg.get("product_themes") or [] if t]
    names = []
    primary_pdf = vocab.clean(md.get("pdffilename"))
    for r in pkg.get("resources") or []:
        url = r.get("url") or ""
        if r.get("url_type") != "upload" or url.endswith("/download/url"):
            continue
        filename = url.rsplit("/", 1)[-1]
        local = mirror_root / "packages" / pkg["name"] / filename
        if not local.exists():
            alt = mirror_root / "packages" / pkg["name"] / f"{r.get('id')}-{filename}"
            local = alt if alt.exists() else None
        role, label = classify(r.get("name") or filename, primary_pdf)
        names.append(r.get("name") or filename)
        p.files.append(ProductFile(role=role, label=label, filename=r.get("name") or filename, path=local, url=url))
    order_files(p.files)
    _fill(p, md, names)
    # CKAN's own description is the fallback for the summary (80% coverage vs 39%)
    p.summary = vocab.clean(md.get("summary")) or (pkg.get("notes") or "").strip()
    if not p.map_number:
        # Legacy records (2016 import) have no map number; their CKAN ref is not unique, the package name is
        p.map_number = pkg["name"]
    return p


def from_zip(name: str, members: dict) -> Product:
    """members: {basename: bytes} of one product ZIP (see other/loader/load_products.py read_products)."""
    xml_name = next(n for n in members if n.lower().endswith(".xml"))
    root = ET.fromstring(members[xml_name].decode("utf-8-sig")).find("mapdata")
    if root is None:
        raise ValueError(f"{xml_name}: no <mapdata>")
    md = {c.tag: (c.text or "").strip() for c in root if c.tag != "themes"}
    md["themes"] = [(t.text or "").strip() for t in root.findall("themes/theme")]
    p = Product(source="zip", source_id=name, emergency_code=md.get("operationID", "").strip())
    try:
        p.version = int(md.get("versionNumber") or 1)
    except ValueError:
        p.version = 1
    # The add-on's XML themes mix product themes ("Situational Awareness") with hazard words ("Hydrological",
    # "Flash Flood"). Hazards come from GLIDE (Hazard filter), so only the product themes are kept as Theme.
    hazard_words = {w.lower() for w in vocab.HAZARD_WORDS}
    p.themes = [t for t in md["themes"] if t and t.lower() not in hazard_words]
    new_terms = [t for t in p.themes if t not in vocab.THEMES]
    if new_terms:
        p.warnings.append(f"themes not in CKAN's list (added to the Theme filter): {', '.join(new_terms)}")
    primary_pdf = md.get("pdffilename", "")
    for fname, data in members.items():
        if fname == xml_name:
            continue
        role, label = classify(fname, primary_pdf)
        p.files.append(ProductFile(role=role, label=label, filename=fname, data=data))
    order_files(p.files)
    return _fill(p, md, list(members))


def read_zip_products(name, blob):
    """(zip name, {member basename: bytes}) per product in a product ZIP or a ZIP of product ZIPs."""
    z = zipfile.ZipFile(io.BytesIO(blob))
    names = [i.filename for i in z.infolist() if not i.is_dir()]
    if any(n.lower().endswith(".xml") for n in names):
        yield name, {pathlib.PurePath(n).name: z.read(n) for n in names}
        return
    for n in sorted(names):
        if n.lower().endswith(".zip"):
            yield from read_zip_products(pathlib.PurePath(n).name, z.read(n))
