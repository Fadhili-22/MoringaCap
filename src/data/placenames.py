"""Place-name parsing and the curated place -> county dictionary (shared by the lookup builder and the labels).

Rules: a place maps to a county only if the dictionary says so. Anything else is left UNMAPPED and logged.
Confidence: 'certain' = whole old district / town / spelling variant that sits in exactly one current county;
'probable' = relies on a qualifier, a small locality or a spelling guess, or the text looks inconsistent.
"""
import re

# --- normalisation -------------------------------------------------------------------------------------------

_DROP_WORDS = re.compile(r"\b(districts?|counties|county|provinces?)\b")


def repair_text(s):
    """Fix UTF-8 text that was decoded as latin-1 (e.g. 'KenyaÂ ', 'Rangâ\x80\x99ul')."""
    if not isinstance(s, str):
        return ""
    try:
        s = s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return s.replace(" ", " ")


def norm(s):
    s = repair_text(s).lower()
    s = s.replace("–", "-").replace("—", "-").replace("’", "'").replace("‘", "'").replace("`", "'")
    s = re.sub(r"'s\b", "", s)
    s = _DROP_WORDS.sub(" ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,:;-'\"")


USER_NOTE = "user-confirmed local knowledge"

# Whole fragments whose automatic reading is replaced by a team decision.
FRAGMENT_OVERRIDES = {
    # Budalangi is in Busia only; the DFO text says "of Siaya District" but the team maps it to Busia alone.
    "budalangi division of siaya": [("Busia", "probable", "Budalangi is in Busia only (team decision); text wrongly says Siaya District")],
}

# --- curated dictionary: normalised key -> (county as spelled in the crosswalk, confidence, note) -------------

def _build():
    d = {}

    def add(keys, county, conf="certain", note=""):
        for k in ([keys] if isinstance(keys, str) else keys):
            d[norm(k)] = (county, conf, note)

    # current counties and spelling variants
    for c in ["Mombasa", "Kwale", "Kilifi", "Tana River", "Lamu", "Garissa", "Wajir", "Mandera", "Marsabit", "Isiolo",
              "Meru", "Embu", "Kitui", "Machakos", "Makueni", "Nyandarua", "Nyeri", "Kirinyaga", "Kiambu", "Turkana",
              "West Pokot", "Samburu", "Trans Nzoia", "Uasin Gishu", "Nandi", "Baringo", "Laikipia", "Nakuru", "Narok",
              "Kajiado", "Kericho", "Bomet", "Kakamega", "Vihiga", "Bungoma", "Busia", "Siaya", "Kisumu", "Homa Bay",
              "Migori", "Kisii", "Nyamira", "Nairobi"]:
        add(c, c)
    add(["Taita-Taveta", "Taita Taveta", "Taita", "Taveta"], "Taita-Taveta")
    add(["Tharaka-Nithi", "Tharaka Nithi", "Tharaka"], "Tharaka-Nithi")
    add(["Elgeyo-Marakwet", "Elgeyo Marakwet", "Keiyo", "Marakwet", "Keiyo/Marakwet"], "Elgeyo-Marakwet", note="Keiyo/Marakwet were districts of today's county")
    add(["Murang'a", "Muranga", "Maragua"], "Murang'a", note="Muranga = spelling variant; Maragua = old district")
    add(["Trans-Nzoia", "Transnzoia"], "Trans Nzoia")
    add(["Homabay"], "Homa Bay")
    add("Mobasa", "Mombasa", note="typo for Mombasa")
    add("Kerhicho", "Kericho", note="typo for Kericho")
    add("Tarkana", "Turkana", note="typo for Turkana")
    add("Wajir", "Wajir")
    # old districts -> current county
    add(["Nyando", "Nyakach", "Muhoroni", "Ahero"], "Kisumu", note="Nyando district / its towns are in Kisumu county")
    add(["Kano"], "Kisumu", "probable", "Kano plains assumed to be the Kano plains in Nyando/Kisumu")
    add(["Manyatta", "Manyattta", "Nyalenda", "Dunga"], "Kisumu", "probable", "Kisumu city settlements (relies on the text saying Kisumu)")
    add(["Rachuonyo", "Karachuonyo", "Rangwe", "Suba"], "Homa Bay", note="old district in Homa Bay county")
    add(["Rarieda", "Ugenya", "Alego Usonga", "Alego-Usonga", "Alego"], "Siaya", note="old district / constituency in Siaya")
    add(["Nyatike", "Uriri", "Kuria"], "Migori", note="old district in Migori county")
    add(["Budalangi", "Bunyala"], "Busia", note="Budalangi/Bunyala are in Busia county")
    add(["Central Kisii", "Kisii Central", "Gucha"], "Kisii", note="old district in Kisii county")
    add(["Nandi North", "Nandi South", "Nandi East", "Nandi Central"], "Nandi", note="old district")
    add(["Meru Central", "Meru North"], "Meru", note="old district in Meru county")
    add(["Meru South"], "Tharaka-Nithi", note="Meru South district became part of Tharaka-Nithi county")
    add(["Mt Elgon", "Mount Elgon"], "Bungoma", note="Mt Elgon district is in Bungoma county")
    add(["Koibatek", "Mogotio", "Marigat", "East Pokot", "East Baringo", "Eldama Ravine"], "Baringo", note="old district / town in Baringo county")
    add(["Pokot Central", "Pokot North", "Pokot South", "North Pokot", "South Pokot", "Central Pokot"], "West Pokot", "probable",
        "Pokot Central/North/South districts assumed to be inside West Pokot; plain 'Pokot' is NOT mapped (could be Baringo)")
    add(["Thika"], "Kiambu", note="Thika district is in Kiambu county")
    add(["Malindi", "Kaloleni", "Kikambala"], "Kilifi", note="old district / town in Kilifi county")
    add(["Kinango", "Matuga", "Msambweni"], "Kwale", note="old district / town in Kwale county")
    add(["Ramisi"], "Kwale", "probable", "Ramisi assumed to be Ramisi in Kwale (text pairs it with Kwale)")
    add(["Likoni", "Kisauni", "Changamwe", "Kipevu"], "Mombasa", note="Mombasa sub-county / area")
    add(["Mshomoroni", "Mushomoroni", "Mishoromoni", "Junda"], "Mombasa", "probable", "Mombasa locality; spelling variants of Mshomoroni")
    add(["Mazeras"], "Kilifi", "probable", "Mazeras is in Kilifi county (Rabai) but text lists it with Kwale/Kilifi")
    add(["Witu", "Mpeketoni"], "Lamu", note="Lamu county towns")
    add(["Tana Delta", "Garsen", "Hola", "Madogo"], "Tana River", note="Tana River county town / old district")
    add(["Bura", "Wenje"], "Tana River", "probable", "small Tana River settlements")
    add(["Voi", "Wundanyi", "Mwatate"], "Taita-Taveta", note="Taita-Taveta towns")
    add(["Dadaab", "Daadab", "Hagadera", "Ifo", "Ijara"], "Garissa", note="Garissa county place / old district")
    add(["Merti"], "Isiolo", note="Merti is in Isiolo county")
    add(["Moyale", "North Horr", "Chalbi"], "Marsabit", note="old district / constituency in Marsabit county")
    add(["Bubisa", "Mubisa"], "Marsabit", "probable", "Bubisa/Mubisa locality in North Horr, Marsabit")
    add(["Kitale"], "Trans Nzoia", note="Kitale town")
    add(["Molo"], "Nakuru", note="Molo district is in Nakuru county")
    add(["Kibera", "Dagoretti"], "Nairobi", note="Nairobi area")

    # --- user-confirmed local knowledge (team decision, 29 Oct 2026) ---
    def uc(keys, county):
        add(keys, county, "probable", USER_NOTE)

    uc(["osuret", "kamolo", "amoni", "asing'e", "hakati", "magombe", "makunda a", "makunda b", "makhunda",
        "nzoia river", "bundalangi area in nyanza"], "Busia")
    uc(["asego", "got kokech", "kawadhgone", "kawadhgone nyongo", "koyugi", "wagwe", "kochogo"], "Homa Bay")
    uc(["pap onditi", "asalo", "kakola", "miwani", "ombeyi", "awach river", "ayweyo"], "Kisumu")
    uc(["kimorigo", "mahoo", "mbogoni"], "Taita-Taveta")
    uc(["kau", "ozi", "mnazini", "mnazini bahati", "hweani"], "Tana River")
    uc(["namanjalala"], "Trans Nzoia")
    uc(["gafarsa"], "Isiolo")
    uc(["malkagala"], "Marsabit")
    uc(["kiembeni"], "Mombasa")
    uc(["villages neighbouring the yala swamp"], "Siaya")
    uc(["chepsigot", "kerio valley"], "Elgeyo-Marakwet")
    uc(["eldume", "ng'ambo"], "Baringo")
    return d


DICT = _build()
KEYS_LONGEST_FIRST = sorted(DICT, key=len, reverse=True)

# Names that are provinces/regions/countries or other things we deliberately do NOT map.
NOT_A_COUNTY = {
    "nyanza", "western", "rift valley", "coast", "central", "eastern", "north eastern", "north-eastern", "northeastern",
    "western kenya", "north rift", "eastern kenya", "central kenya", "northeastern kenya", "coastal areas", "kenya",
    "mount kenya", "mt kenya", "south nyanza", "nyanza province", "rift valley province", "coast province",
}
AMBIGUOUS = {
    "rongai": "Rongai exists in both Nakuru and Kajiado",
    "githurai": "Githurai straddles the Nairobi/Kiambu boundary",
    "pokot": "plain 'Pokot' could be West Pokot or Baringo (East Pokot)",
}

# --- splitting a free-text field into place fragments ---------------------------------------------------------

_COUNTRY = re.compile(r"^(kenya|uganda|tanzania|somalia|ethiopia|sudan)\b\s*[-:]?\s*", re.I)
_SPLIT = re.compile(r"\s+-\s+|\s+–\s+|[,;:()\n]|\.\s+|\.$|\s+and\s+|\s*&\s*|/")


def kenyan_segments(text):
    """Split into segments, keeping only those under a 'Kenya' header (or before any country header)."""
    text = repair_text(text)
    keep, dropped, in_kenya = [], [], True
    for seg in re.split(r"\n|--", text):
        s = seg.strip()
        if not s:
            continue
        m = _COUNTRY.match(s)
        if m:
            in_kenya = m.group(1).lower() == "kenya"
            s = s[m.end():]
        (keep if in_kenya else dropped).append(s)
    return keep, dropped


def fragments(text):
    """List of (raw fragment, normalised fragment) for the Kenyan part of a free-text location field."""
    keep, _ = kenyan_segments(text)
    out = []
    for seg in keep:
        for raw in _SPLIT.split(seg):
            n = norm(raw)
            if len(n) > 2 and n not in {"districts", "rivers", "villages", "area", "areas", "kenya"}:
                out.append((raw.strip(), n))
    return out


GENERIC = {"area", "areas", "town", "division", "region", "location", "locations", "constituency", "village",
           "villages", "slums", "ward", "township", "north", "south", "east", "west", "central", "upper", "lower",
           "greater", "sub-county"}


def strip_generic(n):
    """Drop generic words (area, division, North, ...) from both ends of a fragment."""
    words = n.split()
    while words and words[0] in GENERIC:
        words.pop(0)
    while words and words[-1] in GENERIC:
        words.pop()
    return " ".join(words)


def map_fragment(n):
    """Map one normalised fragment -> list of (county or None, confidence, note)."""
    if n in FRAGMENT_OVERRIDES:
        return list(FRAGMENT_OVERRIDES[n])
    if n in DICT:
        county, conf, note = DICT[n]
        return [(county, conf, note)]
    core = strip_generic(n)
    if core and core != n and core in DICT:
        county, conf, note = DICT[core]
        if note == USER_NOTE:
            return [(county, conf, note)]
        return [(county, conf, f"generic word(s) dropped from '{n}'; {note}".strip("; "))]
    if n in AMBIGUOUS:
        return [(None, "unmapped", "ambiguous: " + AMBIGUOUS[n])]
    if n in NOT_A_COUNTY:
        return [(None, "unmapped", "province/region/country, not a single county")]
    hits, taken = [], []
    for k in KEYS_LONGEST_FIRST:
        for m in re.finditer(r"(?<![a-z])" + re.escape(k) + r"(?![a-z])", n):
            if any(m.start() < e and m.end() > s for s, e in taken):
                continue
            taken.append((m.start(), m.end()))
            county, conf, note = DICT[k]
            hits.append((county, "probable", f"'{k}' found inside longer text; {note}".strip("; ")))
    if hits:
        return hits
    if re.search(r"\briver|tributar|\bmarere\b", n):
        return [(None, "unmapped", "river name, not a place")]
    return [(None, "unmapped", "locality not in the dictionary")]
