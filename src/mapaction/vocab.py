"""Controlled vocabularies and clean-up rules, taken from the CKAN data (see METADATA-FIELDS.md)."""
import re

# CKAN product_themes: the 21 values in use (MapAction product catalogue)
THEMES = [
    "Orientation and Reference", "Situation and Damage", "Affected Population", "Who-What-Where",
    "Emergency Shelter", "Health", "Population Baseline", "Logistics", "Environmental Aspects", "Nutrition",
    "Water Sanitation and Hygiene", "Education", "Emergency Telecommunications", "Early Recovery",
    "Search and Rescue or Evacuation Planning", "Agriculture", "Camp Coordination or Management",
    "Search and Rescue Sectors", "Security and Safety and Protection", "P-codes", "Appeals",
]

PRODUCT_TYPES = {"mapsheet": "Map sheet", "atlas": "Atlas", "mapbook": "Map book", "mapseries": "Map series"}

# GLIDE hazard codes (glidenumber.net)
HAZARDS = {
    "EQ": "Earthquake", "TC": "Tropical cyclone", "FL": "Flood", "FF": "Flash flood", "DR": "Drought",
    "EP": "Epidemic", "TS": "Tsunami", "VO": "Volcano", "LS": "Landslide", "MS": "Mud slide", "ST": "Severe storm",
    "WF": "Wild fire", "CE": "Complex emergency", "AC": "Accident", "EC": "Extratropical cyclone", "CW": "Cold wave",
    "HT": "Heat wave", "SS": "Storm surge", "TO": "Tornado", "OT": "Other",
}
# Hazard words the ArcGIS add-on puts among the themes (family and type)
HAZARD_WORDS = set(HAZARDS.values()) | {"Geophysical", "Hydrological", "Meteorological", "Climatological", "Biological",
                                        "Earthquake", "Flood", "Flash Flood", "Epidemic", "Cyclone", "Hurricane", "Storm"}
GLIDE_RE = re.compile(r"^([A-Z]{2})-(\d{4})-(\d{6})-([A-Z]{3})$")

# ISO 639-2 (GeoNode's language field) from what CKAN and the XML carry
LANGUAGES = {"eng": "English", "spa": "Spanish", "fre": "French", "por": "Portuguese", "ara": "Arabic", "dut": "Dutch",
             "ger": "German", "rus": "Russian"}
_LANG_WORDS = {"english": "eng", "england": "eng", "en": "eng", "eng": "eng", "spanish": "spa", "espa": "spa",
               "castilian": "spa", "es": "spa", "spa": "spa", "french": "fre", "fr": "fre", "fre": "fre",
               "portuguese": "por", "pt": "por", "arabic": "ara", "ar": "ara", "dutch": "dut", "flemish": "dut",
               "nl": "dut", "german": "ger", "de": "ger"}

PLACEHOLDERS = {"", "none", "null", "n/a", "na", "unknown", "0", "0000-00-00 00:00:00", "blah de blah", "undetermined"}


def clean(value):
    """Strip and drop placeholder values ('None', 'NULL', 'Blah de blah'…)."""
    if value is None:
        return ""
    value = str(value).strip()
    return "" if value.lower() in PLACEHOLDERS else value


def languages(*values):
    """'Arabic and English' -> ['ara', 'eng']; 'Spanish; Castilian' -> ['spa']; 'Undetermined' -> []."""
    found = []
    for v in values:
        for word in re.findall(r"[a-zA-Z]+", clean(v).lower()):
            code = _LANG_WORDS.get(word)
            if code and code not in found:
                found.append(code)
        if found:
            break
    return found


def glide(value):
    """A valid GLIDE number or ''. CKAN has junk such as 'No', 'n/a', 'tbc'."""
    for part in re.split(r"[,;\s]+", clean(value).upper()):
        if GLIDE_RE.match(part):
            return part
    return ""


def hazard(glide_no):
    m = GLIDE_RE.match(glide_no or "")
    return HAZARDS.get(m.group(1), "") if m else ""


def access_is_public(value):
    return clean(value).lower() == "public"


def product_type(value, filenames=()):
    v = clean(value).lower().replace(" ", "")
    if v in PRODUCT_TYPES:
        return v
    names = " ".join(filenames).lower()
    if "atlas" in names:
        return "atlas"
    if "mapbook" in names:
        return "mapbook"
    return ""
