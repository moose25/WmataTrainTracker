"""Octilinear ("spider map") schematic layout for the Metro diagram.

Instead of hand-placing all ~100 stations, we fix coordinates only for ANCHOR
stations (terminals, interchanges, and corners where a line bends) on a 45/90
grid, then evenly distribute the in-between stations along each straight
segment. This keeps every line straight and angled like the official map.

Grid convention: x grows east, y grows south (matches SVG's y-down), so "up"
on the map is negative y. Units are arbitrary; the frontend scales to fit.
"""

# code -> (x, y). Only anchors; everything else is interpolated between them.
ANCHORS = {
    # --- Blue/Orange/Silver horizontal trunk (y = 0) ---
    "C05": (-4, 0),    # Rosslyn
    "A01": (0, 0),     # Metro Center  (== C01)
    "D03": (3, 0),     # L'Enfant Plaza (== F03)
    "D08": (8, 0),     # Stadium-Armory

    # --- Yellow/Green vertical trunk (x = 3) ---
    "B01": (3, -3),    # Gallery Place (== F01)
    "B06": (3, -10),   # Fort Totten (== E06)

    # --- Red: SW horseshoe + NE arm ---
    "A15": (-14, -14), # Shady Grove (long NW diagonal into Metro Center)
    "B03": (5, -5),    # Union Station (corner)
    "B05": (5, -8),    # Brookland-CUA (corner)
    "B11": (3, -15),   # Glenmont

    # --- Green branches ---
    "F06": (3, 3),     # Anacostia (corner: trunk turns SE)
    "F11": (8, 8),     # Branch Ave
    "E10": (7, -14),   # Greenbelt

    # --- Orange/Silver west ---
    "K05": (-9, 0),    # East Falls Church (OR/SV split): runs west off the trunk
    "K08": (-13, 0),   # Vienna (Orange continues straight west)
    "N12": (-20, -11), # Ashburn (Silver branches NW)

    # --- Orange/Silver/Blue east branches ---
    "D13": (13, -5),   # New Carrollton (Orange)
    "G05": (13, 5),    # Downtown Largo (Silver/Blue)

    # --- Blue/Yellow C-line south ---
    "C07": (-4, 2),    # Pentagon (Yellow joins via bridge)
    "C13": (-4, 7),    # King St-Old Town (Blue/Yellow split)
    "J03": (-6, 9),    # Franconia-Springfield (Blue)
    "C15": (-4, 9),    # Huntington (Yellow)
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
