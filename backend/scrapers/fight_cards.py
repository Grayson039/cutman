"""
fight_cards.py
Scrapes upcoming fight card data from Wikipedia (UFC) and Tapology (all promotions).
"""

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

NETWORK_KEYWORDS = {
    "ufc fight pass": "UFC Fight Pass",
    "ppv":            "PPV",
    "espn+":          "ESPN+",
    "espn":           "ESPN",
    "dazn":           "DAZN",
    "prime video":    "Prime Video",
    "prime":          "Prime Video",
    "hbo":            "HBO",
    "showtime":       "Showtime",
    "paramount":      "Paramount+",
    "fox":            "Fox",
    "tnt":            "TNT",
    "cbs":            "CBS",
    "nbc":            "NBC",
    "one championship app": "ONE App",
    "internet stream": "Stream",
    "fite":           "FITE",
}

# Short promotion abbreviation → display name
PROMO_NAMES = {
    "UFC":     "UFC",
    "PFL":     "PFL",
    "ONE":     "ONE",
    "OFC":     "ONE",          # ONE FC
    "LFA":     "LFA",
    "BKFC":    "BKFC",
    "BNFC":    "BKFC",
    "CG":      "Combate",
    "COMBATE": "Combate",
    "RIZIN":   "RIZIN",
    "CW":      "Cage Warriors",
    "GLORY":   "GLORY",
    "GB":      "Golden Boy",
    "GBP":     "Golden Boy",
    "TR":      "Top Rank",
    "MB":      "Matchroom",
    "MR":      "Matchroom",
    "WOW":     "WOW FC",
}

# Only include promotions in this set (by abbreviation).
# Empty set = show everything.
MAJOR_PROMOS = {
    # MMA
    "UFC", "PFL", "ONE", "OFC", "LFA", "BKFC", "BNFC",
    "CG", "COMBATE", "RIZIN", "CW", "GLORY", "WOW",
    # Boxing — Golden Boy, Top Rank, Matchroom, Queensberry, DiBella, Premier Boxing
    "GB", "GBP", "TR", "MB", "MR", "QB", "QBP", "DBE", "PBC",
    # Boxing — promoter name variants Tapology uses
    "GOLDEN BOY", "TOP RANK", "MATCHROOM", "QUEENSBERRY",
    "PREMIER BOXING", "DIBELLA", "PROBELLUM", "DAZN",
}


def _detect_network(text: str) -> str:
    low = text.lower()
    for key, label in NETWORK_KEYWORDS.items():
        if key in low:
            return label
    return ""


# ─────────────────────────────────────────────────────────────
# Wikipedia — UFC scheduled events
# ─────────────────────────────────────────────────────────────

def scrape_ufc_wikipedia() -> tuple[list[dict], str | None]:
    """
    Returns (events, error). events is a list of dicts:
        promotion, name, date, venue, location, main_event, network
    """
    url = "https://en.wikipedia.org/wiki/List_of_UFC_events"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
    except Exception as e:
        return [], f"Wikipedia fetch failed: {e}"

    soup = BeautifulSoup(resp.text, "html.parser")

    # Find the Scheduled / Upcoming events section
    section_anchor = None
    for heading in soup.find_all(["h2", "h3"]):
        heading_id  = heading.get("id", "").lower()
        heading_txt = heading.get_text().lower()
        if any(kw in heading_id or kw in heading_txt for kw in ("scheduled", "upcoming")):
            section_anchor = heading
            break

    if not section_anchor:
        return [], "Could not locate 'Scheduled/Upcoming events' section on Wikipedia"

    table = section_anchor.find_next("table", class_="wikitable")
    if not table:
        return [], "Could not find events table after scheduled events heading"

    header_row = table.find("tr")
    if not header_row:
        return [], "Empty table"

    headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]

    def col_index(*keywords):
        for i, h in enumerate(headers):
            if any(k in h for k in keywords):
                return i
        return None

    idx_event    = col_index("event")
    idx_date     = col_index("date")
    idx_venue    = col_index("venue", "arena")
    idx_location = col_index("location", "city")
    idx_notes    = col_index("notes", "main event", "card")

    events = []
    date_pattern = re.compile(
        r"(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2},?\s*\d{4}",
        re.IGNORECASE,
    )

    for row in table.find_all("tr")[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue

        texts = [c.get_text(" ", strip=True) for c in cells]

        def get(idx, fallback=""):
            if idx is not None and idx < len(texts):
                return texts[idx].strip()
            return fallback

        event_name = get(idx_event)
        date_raw   = get(idx_date)
        venue      = get(idx_venue)
        location   = get(idx_location)
        notes      = get(idx_notes)

        # Fallback: scan all cells for a date string
        if not date_pattern.search(date_raw):
            for t in texts:
                if date_pattern.search(t):
                    date_raw = t
                    break

        if not event_name or event_name.isdigit():
            event_name = texts[1] if len(texts) > 1 else ""
        if not event_name:
            continue

        events.append({
            "promotion":  "UFC",
            "name":       event_name,
            "date":       date_raw,
            "venue":      venue,
            "location":   location,
            "main_event": notes,
            "network":    _detect_network(notes + " " + event_name),
        })

    return events, None


# ─────────────────────────────────────────────────────────────
# Tapology — all promotions
# ─────────────────────────────────────────────────────────────

ALLOWED_SPORTS = {"mma", "boxing", "kickboxing", "muay thai", "combat sports"}


def scrape_tapology() -> tuple[list[dict], str | None]:
    """
    Scrapes the Tapology fight center for upcoming events across all promotions.
    Filters to MAJOR_PROMOS and combat sports only.
    """
    url = "https://www.tapology.com/fightcenter"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
    except Exception as e:
        return [], f"Tapology fetch failed: {e}"

    soup  = BeautifulSoup(resp.text, "html.parser")
    fc    = soup.find("div", class_="fightcenterEvents")
    if not fc:
        return [], "Tapology: fightcenterEvents container not found"

    rows   = fc.select("div[class*=flex][class*=justify-between]")
    events = []

    date_re = re.compile(
        r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+"
        r"(\w+ \d{1,2},?\s*(?:\d{4},?)?\s*\d{1,2}:\d{2}\s*[AP]M)\s*ET",
        re.IGNORECASE,
    )
    short_re = re.compile(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}", re.IGNORECASE)

    for row in rows:
        full_text = row.get_text(" | ", strip=True)

        # Event name
        event_link = row.find("a", href=re.compile(r"/fightcenter/events/"))
        if not event_link:
            continue
        name = event_link.get_text(strip=True)
        if not name:
            continue

        # Promotion abbreviation from the promo img alt
        promo_link = row.find("a", href=re.compile(r"/fightcenter/promotions/"))
        promo_abbr = ""
        if promo_link:
            img = promo_link.find("img")
            if img:
                promo_abbr = img.get("alt", "").strip().upper()
            if not promo_abbr:
                # Fall back: last path segment without numeric prefix
                slug  = promo_link.get("href", "").split("/")[-1]
                parts = [p for p in slug.split("-") if not p.isdigit()]
                promo_abbr = parts[-1].upper() if parts else ""

        # Filter to major promotions (if whitelist defined)
        if MAJOR_PROMOS and promo_abbr not in MAJOR_PROMOS:
            continue

        # Resolve display name
        promotion = PROMO_NAMES.get(promo_abbr, promo_abbr)

        # Sport type (for filtering)
        sport = "MMA"
        for s in ("Boxing", "Kickboxing", "Muay Thai", "Combat Sports", "MMA"):
            if s.lower() in full_text.lower():
                sport = s
                break
        if sport.lower() not in ALLOWED_SPORTS:
            continue

        # Date
        date_str = ""
        dm = date_re.search(full_text)
        if dm:
            date_str = dm.group(0)
        else:
            sm = short_re.search(full_text)
            if sm:
                date_str = sm.group(0)

        # Main bout
        bout_link  = row.find("a", href=re.compile(r"/fightcenter/bouts/"))
        main_event = bout_link.get_text(strip=True) if bout_link else ""

        # Network
        network = _detect_network(full_text)

        # Location
        location = ""
        loc_re = re.compile(r"([A-Z][a-z]+(?: [A-Z][a-z]+)?,\s*[A-Z]{2})")
        lm = loc_re.search(full_text)
        if lm:
            location = lm.group(0)

        events.append({
            "promotion":  promotion,
            "name":       name,
            "date":       date_str,
            "venue":      "",
            "location":   location,
            "main_event": main_event,
            "network":    network,
        })

    return events, None


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

def get_upcoming_events() -> tuple[list[dict], dict]:
    """
    Merge results from all sources. Wikipedia is primary for UFC;
    Tapology fills in other promotions.
    """
    all_events = []
    errors     = {}

    ufc_events, ufc_err = scrape_ufc_wikipedia()
    errors["wikipedia"] = ufc_err
    all_events.extend(ufc_events)

    tap_events, tap_err = scrape_tapology()
    errors["tapology"] = tap_err

    # Deduplicate: skip Tapology UFC entries if we already have from Wikipedia
    ufc_names = {e["name"].lower() for e in ufc_events}
    for ev in tap_events:
        if ev["promotion"].upper() == "UFC" and ev["name"].lower() in ufc_names:
            continue
        all_events.append(ev)

    return all_events, errors
