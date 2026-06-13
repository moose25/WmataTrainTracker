"""News feed for the hub banner: WMATA service alerts + DC news headlines.

Combines live WMATA rail/elevator incidents with general DC headlines pulled
from a local-news RSS feed (WTOP by default). Network/parse failures degrade
gracefully to an empty list so the banner never breaks the page.
"""

import xml.etree.ElementTree as ET

import requests

DC_NEWS_RSS = "https://wtop.com/feed/"
NEWS_LIMIT = 12


def fetch_dc_news(url=DC_NEWS_RSS, limit=NEWS_LIMIT):
    """Return [{kind: 'news', text, url}] from a DC news RSS feed."""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "wmata-hub/1.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except (requests.RequestException, ET.ParseError):
        return []

    items = []
    for item in root.iterfind(".//item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        items.append({
            "kind": "news",
            "text": title,
            "url": (item.findtext("link") or "").strip(),
        })
        if len(items) >= limit:
            break
    return items


def build_alerts(rail_incidents, elevator_incidents):
    """Turn WMATA incidents into [{kind: 'alert', text}] banner items."""
    items = []
    for inc in rail_incidents:
        lines = (inc.get("LinesAffected") or "").replace(";", " ").split()
        prefix = f"[{' '.join(lines)}] " if lines else ""
        desc = (inc.get("Description") or "").strip()
        if desc:
            items.append({"kind": "alert", "text": f"{prefix}{desc}"})
    for e in elevator_incidents:
        unit = e.get("UnitType") or "UNIT"
        station = e.get("StationName") or ""
        symptom = e.get("SymptomDescription") or ""
        items.append({"kind": "alert", "text": f"{unit} at {station}: {symptom}"})
    return items


def build_news(rail_incidents, elevator_incidents):
    """Alerts first, then DC headlines."""
    return build_alerts(rail_incidents, elevator_incidents) + fetch_dc_news()
