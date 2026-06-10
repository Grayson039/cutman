"""
fighters.py
Scrapes fighter profiles and search results from Sherdog.com.

Sources:
  Search  — sherdog.com/stats/fightfinder?SearchTxt=<name>
  Profile — sherdog.com/fighter/<Slug-ID>
"""

import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

BASE = "https://www.sherdog.com"


# ─────────────────────────────────────────────────────────────
# Search
# ─────────────────────────────────────────────────────────────

def search_fighters(name: str) -> tuple[list[dict], str | None]:
    """
    Search Sherdog for fighters matching `name`.

    Returns (results, error).
    Each result: { name, slug, height, weight, association, url }
    """
    url = f"{BASE}/stats/fightfinder?SearchTxt={requests.utils.quote(name)}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
    except Exception as e:
        return [], f"Search request failed: {e}"

    soup    = BeautifulSoup(resp.text, "html.parser")
    results = []

    table = soup.find("table", class_="fightfinder_result")
    if not table:
        return [], f"No fighters found for '{name}'"

    for row in table.find_all("tr")[1:]:   # skip header
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        link = row.find("a", href=re.compile(r"/fighter/"))
        if not link:
            continue

        href        = link.get("href", "")
        slug        = href.strip("/").split("/")[-1]   # e.g. Jon-Jones-27944
        f_name      = link.get_text(strip=True)        # name is the link text
        nickname    = cells[1].get_text(strip=True) if len(cells) > 1 else ""
        height      = cells[2].get_text(strip=True) if len(cells) > 2 else ""
        weight      = cells[3].get_text(strip=True) if len(cells) > 3 else ""
        association = cells[4].get_text(strip=True) if len(cells) > 4 else ""

        results.append({
            "name":        f_name,
            "nickname":    nickname,
            "slug":        slug,
            "height":      height,
            "weight":      weight,
            "association": association,
            "url":         BASE + href,
        })

    if not results:
        return [], f"No fighters found for '{name}'"

    return results, None


# ─────────────────────────────────────────────────────────────
# Profile
# ─────────────────────────────────────────────────────────────

def get_fighter_profile(slug: str) -> tuple[dict | None, str | None]:
    """
    Scrape a full fighter profile from Sherdog.

    `slug` is the Sherdog URL slug, e.g. 'Jon-Jones-27944'

    Returns (profile, error).
    Profile keys:
        name, nickname, age, dob, height, weight,
        weight_class, association, nationality,
        wins, losses, draws, no_contests,
        wins_by_ko, wins_by_sub, wins_by_dec,
        losses_by_ko, losses_by_sub, losses_by_dec,
        fight_history (list of fight dicts), url
    """
    url = f"{BASE}/fighter/{slug}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
    except Exception as e:
        return None, f"Profile fetch failed: {e}"

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── Name + nickname ──────────────────────────────────────
    name     = ""
    nickname = ""

    name_el = soup.find(class_="fn")
    if name_el:
        name = name_el.get_text(strip=True)

    nick_el = soup.find(class_="nickname")
    if nick_el:
        nickname = nick_el.get_text(strip=True).strip('"').strip("'")

    if not name:
        h1 = soup.find("h1")
        if h1:
            name = h1.get_text(strip=True)

    # ── Bio table (age, dob, height, weight, association) ────
    age         = ""
    dob         = ""
    height      = ""
    weight      = ""
    association = ""
    nationality = ""
    weight_class = ""

    bio_table = soup.find("table", class_=lambda c: c is None or "bio" in (c or "").lower())
    if not bio_table:
        # Bio is often the first borderless table on the page
        bio_table = soup.find("table")

    if bio_table:
        cells = bio_table.find_all("td")
        labels = [c.get_text(strip=True).lower() for c in cells]
        for i, label in enumerate(labels):
            val_el = cells[i + 1] if i + 1 < len(cells) else None
            val    = val_el.get_text(strip=True) if val_el else ""

            if "age" in label and not age:
                age = val
            elif "birth" in label or label == "dob":
                dob = val
            elif "height" in label:
                height = val
            elif "weight" in label and "class" not in label:
                weight = val
            elif "association" in label or "team" in label or "gym" in label:
                association = val
            elif "nation" in label or "country" in label:
                nationality = val
            elif "class" in label:
                weight_class = val

    # ── Record counts ────────────────────────────────────────
    wins = losses = draws = no_contests = 0

    # Sherdog renders the record in a section with W / L / D / NC labels
    record_section = soup.find(class_=re.compile(r"record|wld", re.I))
    if record_section:
        nums = re.findall(r"\b(\d+)\b", record_section.get_text())
        if len(nums) >= 3:
            wins, losses, draws = int(nums[0]), int(nums[1]), int(nums[2])
            no_contests = int(nums[3]) if len(nums) > 3 else 0
    else:
        # Fall back: count results directly from fight history
        pass   # filled in after parsing fight_history

    # ── Fight history ─────────────────────────────────────────
    fight_history = _scrape_fight_history(soup)

    # If record section wasn't found, derive from history
    if wins == 0 and losses == 0 and fight_history:
        for f in fight_history:
            r = f["result"].upper()
            if r == "W":
                wins += 1
            elif r == "L":
                losses += 1
            elif r == "D":
                draws += 1
            elif r == "NC":
                no_contests += 1

    # ── Win/loss method breakdown ────────────────────────────
    wins_by_ko  = wins_by_sub  = wins_by_dec  = 0
    losses_by_ko = losses_by_sub = losses_by_dec = 0

    for f in fight_history:
        method = f.get("method", "").upper()
        result = f.get("result", "").upper()
        is_ko  = any(k in method for k in ("KO", "TKO"))
        is_sub = "SUB" in method or "SUBMISSION" in method
        is_dec = "DEC" in method or "DECISION" in method or "UNANIMOUS" in method or "SPLIT" in method

        if result == "W":
            if is_ko:  wins_by_ko  += 1
            elif is_sub: wins_by_sub += 1
            elif is_dec: wins_by_dec += 1
        elif result == "L":
            if is_ko:  losses_by_ko  += 1
            elif is_sub: losses_by_sub += 1
            elif is_dec: losses_by_dec += 1

    profile = {
        "name":          name,
        "nickname":      nickname,
        "age":           age,
        "dob":           dob,
        "height":        height,
        "weight":        weight,
        "weight_class":  weight_class,
        "association":   association,
        "nationality":   nationality,
        "wins":          wins,
        "losses":        losses,
        "draws":         draws,
        "no_contests":   no_contests,
        "wins_by_ko":    wins_by_ko,
        "wins_by_sub":   wins_by_sub,
        "wins_by_dec":   wins_by_dec,
        "losses_by_ko":  losses_by_ko,
        "losses_by_sub": losses_by_sub,
        "losses_by_dec": losses_by_dec,
        "fight_history": fight_history,
        "url":           url,
    }

    if not name:
        return None, f"Could not parse fighter page for slug '{slug}'"

    return profile, None


def _scrape_fight_history(soup: BeautifulSoup) -> list[dict]:
    """
    Parse fight history from Sherdog's main fighter table.

    Columns: result | opponent | event + date | method | round | time
    Each fight: { result, opponent, opponent_url, event, date, method, round, time }
    """
    fights = []

    table = soup.find("table", class_="new_table")
    if not table:
        return fights

    rows = table.find_all("tr")
    for row in rows[1:]:   # skip header
        cells = row.find_all("td")
        if len(cells) < 5:
            continue

        # Result
        result_raw = cells[0].get_text(strip=True).lower()
        result_map = {"win": "W", "loss": "L", "draw": "D", "no contest": "NC", "nc": "NC"}
        result     = result_map.get(result_raw, result_raw.upper()[:1])

        # Opponent
        opp_link    = cells[1].find("a")
        opponent     = cells[1].get_text(strip=True)
        opponent_url = BASE + opp_link.get("href", "") if opp_link else ""

        # Event + date (combined in one cell on Sherdog)
        event_cell = cells[2]
        event_link = event_cell.find("a")
        event      = event_link.get_text(strip=True) if event_link else ""
        # Date is usually the remaining text after the event link
        date_raw   = event_cell.get_text(" ", strip=True)
        date       = ""
        date_m     = re.search(
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*/\s*\d{1,2}\s*/\s*\d{4}",
            date_raw, re.I
        )
        if date_m:
            date = date_m.group(0)
        else:
            # Try "Month DD, YYYY"
            date_m2 = re.search(
                r"(January|February|March|April|May|June|July|August|"
                r"September|October|November|December)\s+\d{1,2},?\s*\d{4}",
                date_raw, re.I
            )
            if date_m2:
                date = date_m2.group(0)

        # Method — Sherdog appends referee name + "VIEW PLAY-BY-PLAY" after closing paren
        method_raw = cells[3].get_text(strip=True) if len(cells) > 3 else ""
        paren_end  = method_raw.rfind(")")
        method     = method_raw[: paren_end + 1].strip() if paren_end != -1 else method_raw

        # Round
        round_no = cells[4].get_text(strip=True) if len(cells) > 4 else ""

        # Time
        time_str = cells[5].get_text(strip=True) if len(cells) > 5 else ""

        if not opponent and not event:
            continue

        fights.append({
            "result":       result,
            "opponent":     opponent,
            "opponent_url": opponent_url,
            "event":        event,
            "date":         date,
            "method":       method,
            "round":        round_no,
            "time":         time_str,
        })

    return fights
