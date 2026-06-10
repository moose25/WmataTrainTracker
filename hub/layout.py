"""Octilinear ("spider map") schematic layout for the Metro diagram.

Coordinates trace the official WMATA map: anchor stations (terminals,
interchanges, bends) are placed at the map's actual proportional positions, and
the stations between two anchors are evenly interpolated along the straight
segment. Shared stations resolve consistently because the bracketing anchors are
identical across lines (and interchange codes are aliased to one point).

Grid convention: x grows east, y grows south (matches SVG y-down), so "up" on the
map is negative y. Units are arbitrary (image pixels / 10); the frontend scales.
"""

# Interchange stations appear under two codes (one per line); pin both to the
# same point so transfers don't render as two dots.
_METRO_CENTER = (56.5, 43.8)   # A01 / C01
_GALLERY_PLACE = (65.5, 41.5)  # B01 / F01
_LENFANT = (60.5, 60.0)        # D03 / F03
_FORT_TOTTEN = (70.5, 29.5)    # B06 / E06

# code -> (x, y). Only anchors; everything else is interpolated between them.
ANCHORS = {
    # --- core interchanges (both codes aliased) ---
    "A01": _METRO_CENTER, "C01": _METRO_CENTER,
    "B01": _GALLERY_PLACE, "F01": _GALLERY_PLACE,
    "D03": _LENFANT, "F03": _LENFANT,
    "B06": _FORT_TOTTEN, "E06": _FORT_TOTTEN,

    # --- Red: SW diagonal + wiggly NE arm ---
    "A15": (25.5, 11.0),   # Shady Grove
    "A08": (38.8, 30.0),   # Friendship Heights (slight steepening)
    "A02": (50.8, 41.0),   # Farragut North (eases into Metro Center)
    "B03": (70.0, 44.2),   # Union Station (east bow)
    "B05": (68.0, 34.7),   # Brookland-CUA
    "B08": (58.5, 16.5),   # Silver Spring (arm turns up to Glenmont)
    "B11": (61.7, 6.2),    # Glenmont

    # --- Blue/Orange/Silver trunk ---
    "C04": (49.8, 43.0),   # Foggy Bottom (before the river dip)
    "C05": (33.5, 46.2),   # Rosslyn
    "D08": (81.8, 51.5),   # Stadium-Armory

    # --- Yellow/Green north (the Columbia Heights jut) ---
    "E01": (65.5, 40.0),   # Mt Vernon Sq
    "E03": (63.5, 33.2),   # U Street
    "E04": (60.0, 31.8),   # Columbia Heights
    "E05": (61.8, 27.8),   # Georgia Ave-Petworth

    # --- Green branches ---
    "F04": (60.0, 65.0),   # Waterfront (trunk turns SE)
    "F06": (72.5, 68.5),   # Anacostia
    "F11": (90.0, 73.5),   # Branch Ave
    "E10": (80.0, 18.4),   # Greenbelt

    # --- Orange/Silver west ---
    "K05": (23.5, 53.3),   # East Falls Church (OR/SV split)
    "K08": (15.5, 48.8),   # Vienna
    "N12": (9.5, 28.7),    # Ashburn (Dulles corridor, NW)

    # --- Orange/Silver/Blue east branches ---
    "D13": (103.0, 41.6),  # New Carrollton (Orange, NE)
    "G05": (105.5, 53.0),  # Downtown Largo (Silver/Blue, E)

    # --- Blue/Yellow C-line south ---
    "C07": (52.0, 65.0),   # Pentagon (Yellow leaves via the bridge)
    "C09": (52.0, 74.5),   # Crystal City (line shifts toward King St)
    "C13": (56.8, 81.7),   # King St-Old Town (Blue/Yellow split)
    "J03": (37.0, 89.3),   # Franconia-Springfield (Blue, SW)
    "C15": (59.5, 89.3),   # Huntington (Yellow, S)
}


# Stations missing from WMATA's StandardRoutes ordering (the feed lags new
# openings). Insert `code` immediately after `after` on the given line.
MISSING_STATIONS = {
    "BL": [("C10", "C11")],  # Potomac Yard (between National Airport & Crystal City)
    "YL": [("C10", "C11")],
}


def insert_missing(line_code, ordered):
    """Return `ordered` with any known-missing stations spliced in."""
    for after, code in MISSING_STATIONS.get(line_code, []):
        if code not in ordered and after in ordered:
            ordered = ordered[:]
            ordered.insert(ordered.index(after) + 1, code)
    return ordered


def build_coords(lines, stations):
    """Return {code: (x, y)} for every station on the given lines.

    For each line we walk its ordered stations, find the anchored ones, and
    linearly interpolate the stations between each consecutive anchor pair.
    Shared stations resolve to the same point because the bracketing anchors
    (and the stations between them) are identical across lines.
    """
    coords = {}
    for line in lines:
        seq = line["stations"]
        anchor_idx = [i for i, c in enumerate(seq) if c in ANCHORS]
        if not anchor_idx:
            continue
        for a, b in zip(anchor_idx, anchor_idx[1:]):
            ax, ay = ANCHORS[seq[a]]
            bx, by = ANCHORS[seq[b]]
            span = b - a
            for k in range(a, b + 1):
                t = (k - a) / span
                coords[seq[k]] = (ax + (bx - ax) * t, ay + (by - ay) * t)
    return coords
