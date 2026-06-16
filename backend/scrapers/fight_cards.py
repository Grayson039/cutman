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

        # Capture the event's own Wikipedia article link (used to fetch its
        # announced/results fight card later) from the Event column's cell.
        wiki_url = ""
        if idx_event is not None and idx_event < len(cells):
            link = cells[idx_event].find("a", href=True)
            if link and link["href"].startswith("/wiki/"):
                wiki_url = "https://en.wikipedia.org" + link["href"]

        events.append({
            "promotion":  "UFC",
            "name":       event_name,
            "date":       date_raw,
            "venue":      venue,
            "location":   location,
            "main_event": notes,
            "network":    _detect_network(notes + " " + event_name),
            "wiki_url":   wiki_url,
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
            "wiki_url":   "",
        })

    return events, None


# ─────────────────────────────────────────────────────────────
# Event detail — full bout list + fighter photos (Wikipedia)
# ─────────────────────────────────────────────────────────────

import concurrent.futures

_CHAMPION_RE = re.compile(r"\s*\(c\)\s*", re.IGNORECASE)


def _fetch_fighter_photo(wiki_path: str) -> str:
    """Given a /wiki/Fighter_Name path, return the infobox photo URL (or '')."""
    try:
        resp = requests.get("https://en.wikipedia.org" + wiki_path, headers=HEADERS, timeout=8)
        resp.raise_for_status()
    except Exception:
        return ""
    soup = BeautifulSoup(resp.text, "html.parser")
    infobox = soup.find("table", class_="infobox")
    if not infobox:
        return ""
    img = infobox.find("img")
    if not img or not img.get("src"):
        return ""
    src = img["src"]
    return "https:" + src if src.startswith("//") else src


def _make_fighter(raw_name: str, link_map: dict) -> dict:
    is_champ = bool(_CHAMPION_RE.search(raw_name))
    name = _CHAMPION_RE.sub("", raw_name).strip()
    href = link_map.get(name.lower(), "")
    return {"name": name, "champion": is_champ, "wiki_path": href, "photo": ""}


def _parse_announced_bouts(ul) -> list[dict]:
    """Upcoming event: <ul><li>Weight class bout: A vs. B</li>...</ul>"""
    bouts = []
    bout_re = re.compile(r"^(.*?)\s*bout:\s*(.+)$", re.IGNORECASE)
    for li in ul.find_all("li"):
        text = li.get_text(" ", strip=True)
        text = re.sub(r"\s*\[\s*\d+\s*\]\s*$", "", text)  # strip trailing [6] citation
        m = bout_re.match(text)
        if not m:
            continue
        weight_class, matchup = m.group(1).strip(), m.group(2).strip()
        sides = re.split(r"\s+vs\.?\s+", matchup, maxsplit=1)
        if len(sides) != 2:
            continue
        link_map = {a.get_text(strip=True).lower(): a["href"]
                    for a in li.find_all("a") if a.get("href", "").startswith("/wiki/")}
        bouts.append({
            "section": "main",
            "weight_class": weight_class,
            "title": "(c)" in matchup.lower(),
            "method": "", "round": None, "time": "",
            "fighter_a": _make_fighter(sides[0], link_map),
            "fighter_b": _make_fighter(sides[1], link_map),
        })
    return bouts


def _parse_results_table(table) -> list[dict]:
    """Completed event: rows of [weight, fighterA, 'def.', fighterB, method, round, time, notes]."""
    bouts = []
    section = "main"
    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) == 1:
            label = cells[0].get_text(" ", strip=True).lower()
            if "prelim" in label:
                section = "prelim"
            elif "main" in label:
                section = "main"
            continue
        if len(cells) < 7:
            continue
        texts = [c.get_text(" ", strip=True) for c in cells]
        weight_class, a_raw, vs_word, b_raw, method, round_, time_ = texts[:7]
        if not weight_class or weight_class.lower() == "weight class":
            continue
        link_map = {a.get_text(strip=True).lower(): a["href"]
                    for a in row.find_all("a") if a.get("href", "").startswith("/wiki/")}
        fighter_a = _make_fighter(a_raw, link_map)
        fighter_b = _make_fighter(b_raw, link_map)
        fighter_a["winner"] = True
        fighter_b["winner"] = False
        bouts.append({
            "section": section,
            "weight_class": weight_class,
            "title": "(c)" in (a_raw + b_raw).lower(),
            "method": method,
            "round": int(round_) if round_.isdigit() else None,
            "time": time_,
            "fighter_a": fighter_a,
            "fighter_b": fighter_b,
        })
    return bouts


def get_event_card(wiki_url: str) -> tuple[list[dict], str | None]:
    """
    Fetch an event's own Wikipedia page and return its bout list.
    Upcoming events use the 'Announced bouts' bullet list (no result yet);
    completed events use the 'Results' table (includes method/round/time).
    Each fighter gets a best-effort Wikipedia infobox photo.
    """
    if not wiki_url.startswith("https://en.wikipedia.org/wiki/"):
        return [], "Invalid wiki_url"

    try:
        resp = requests.get(wiki_url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
    except Exception as e:
        return [], f"Event page fetch failed: {e}"

    soup = BeautifulSoup(resp.text, "html.parser")

    bouts: list[dict] = []

    results_heading = soup.find(id="Results")
    if results_heading:
        table = results_heading.find_next("table", class_="toccolours")
        if table:
            bouts = _parse_results_table(table)

    if not bouts:
        for heading in soup.find_all(["h2", "h3"]):
            hid = (heading.get("id", "") + heading.get_text()).lower()
            if "announced" in hid or "fight card" in hid:
                container = heading.find_parent("div", class_="mw-heading") or heading
                ul = container.find_next_sibling("ul")
                if ul:
                    bouts = _parse_announced_bouts(ul)
                break

    if not bouts:
        return [], "No fight card found on event page"

    # Resolve fighter photos concurrently (best-effort, missing photo = initials fallback on frontend)
    fighters = []
    for b in bouts:
        for key in ("fighter_a", "fighter_b"):
            if b[key]["wiki_path"]:
                fighters.append(b[key])

    def resolve(f):
        f["photo"] = _fetch_fighter_photo(f["wiki_path"])
        return f

    if fighters:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(resolve, fighters))

    for b in bouts:
        for key in ("fighter_a", "fighter_b"):
            b[key].pop("wiki_path", None)

    return bouts, None


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
