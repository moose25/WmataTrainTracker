"""Octilinear ("spider map") schematic layout for the Metro diagram.

A faithful recreation of the official WMATA map's geometry: the Metro Center /
Gallery Place / L'Enfant core triangle, the river dip to Rosslyn, the horizontal
Blue/Orange/Silver trunk, the vertical Yellow/Green trunk, the Red horseshoe, and
the western/eastern branches at their real angles.

We fix coordinates only for ANCHOR stations (terminals, interchanges, and bends)
on a 45/90 grid; the stations between two anchors are evenly interpolated along
the straight segment. Shared stations resolve consistently because the bracketing
anchors are identical across lines.

Grid convention: x grows east, y grows south (matches SVG y-down), so "up" on the
map is negative y. Units are arbitrary; the frontend scales to fit.
"""

# code -> (x, y). Only anchors; everything else is interpolated between them.
ANCHORS = {
    # --- core triangle ---
    "A01": (22, 26),   # Metro Center (== C01)
    "B01": (25, 23),   # Gallery Place (== F01)
    "D03": (25, 29),   # L'Enfant Plaza (== F03)

    # --- Blue/Orange/Silver trunk ---
    "C04": (16, 26),   # Foggy Bottom (bend before the river dip)
    "C05": (14, 28),   # Rosslyn (river dip / 3-way junction)
    "D08": (35, 29),   # Stadium-Armory

    # --- Red: SW horseshoe + NE arm ---
    "A15": (16, 4),    # Shady Grove (drops vertically, then bends SE into the core)
    "A07": (16, 20),   # Tenleytown-AU (bend: vertical leg meets the SE diagonal)
    "B03": (27, 21),   # Union Station (corner of the east bow)
    "B05": (27, 15),   # Brookland-CUA (corner of the east bow)
    "B06": (25, 13),   # Fort Totten (== E06)
    "B11": (25, 3),    # Glenmont

    # --- Yellow/Green vertical trunk continues up to Fort Totten via B06 ---

    # --- Green branches ---
    "F06": (25, 35),   # Anacostia (trunk turns SE)
    "F11": (35, 45),   # Branch Ave
    "E10": (33, 5),    # Greenbelt

    # --- Orange/Silver west ---
    "K05": (4, 18),    # East Falls Church (OR/SV split)
    "K08": (-2, 18),   # Vienna (Orange runs west)
    "N12": (-18, -4),  # Ashburn (Silver runs NW up the Dulles corridor)

    # --- Orange/Silver/Blue east branches ---
    "D13": (45, 19),   # New Carrollton (Orange, NE)
    "G05": (45, 39),   # Downtown Largo (Silver/Blue, SE)

    # --- Blue/Yellow C-line south ---
    "C07": (14, 34),   # Pentagon (Yellow leaves via the bridge to L'Enfant)
    "C13": (14, 46),   # King St-Old Town (Blue/Yellow split)
    "J03": (10, 50),   # Franconia-Springfield (Blue, SW)
    "C15": (14, 50),   # Huntington (Yellow, S)
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
