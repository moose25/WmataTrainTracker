"""Builds the schematic diagram geometry and places live trains on it.

Two jobs:
  1. Static geometry  -> station coordinates + ordered per-line polylines, derived
     once from rail stations + StandardRoutes.
  2. Live placement   -> turn Train Positions (reported by track circuit) into
     interpolated (lat, lon) points gliding between stations, using the ordered
     circuit->station sequence from StandardRoutes.

Coordinates are raw lat/lon; the frontend projects them to its canvas.
"""

# WMATA line colors (hex) for the frontend.
LINE_HEX = {
    "RD": "#e51937",  # Red
    "BL": "#0076bf",  # Blue
    "OR": "#f7941e",  # Orange
    "SV": "#a2a4a1",  # Silver
    "GR": "#00b04f",  # Green
    "YL": "#ffd200",  # Yellow
}

# Fixed lane offsets so lines that share a trunk draw as parallel colored tracks
# instead of overlapping into one color. Units are "lanes"; the frontend scales
# them to pixels and offsets perpendicular to each segment.
LINE_LANE = {
    "RD": 0.0,
    "BL": 1.0,
    "OR": -1.0,
    "SV": 0.0,
    "YL": -0.6,
    "GR": 0.6,
}

LINE_ORDER = ["RD", "OR", "SV", "BL", "YL", "GR"]


class Diagram:
    """Static diagram geometry, plus the index needed to place trains."""

    def __init__(self, client):
        self.client = client
        self.stations = {}          # code -> {code, name, lat, lon, lines:[...]}
        self.lines = []             # [{code, color, lane, stations:[codes]}]
        self._routes = {}           # (LineCode, TrackNum) -> ordered TrackCircuits
        self._circuit_index = {}    # circuitId -> list of ((LineCode,TrackNum), seq_index)
        self.build()

    # --- build static geometry ---------------------------------------------
    def build(self):
        for s in self.client.rail_stations():
            lines = [s.get(f"LineCode{i}") for i in range(1, 5)]
            together = [s.get("StationTogether1"), s.get("StationTogether2")]
            self.stations[s["Code"]] = {
                "code": s["Code"],
                "name": s["Name"],
                "lat": s["Lat"],
                "lon": s["Lon"],
                "lines": [code for code in lines if code],
                "together": [c for c in together if c],
            }

        routes = self.client.standard_routes()
        for r in routes:
            key = (r["LineCode"], r["TrackNum"])
            seq = r["TrackCircuits"]
            self._routes[key] = seq
            for i, tc in enumerate(seq):
                self._circuit_index.setdefault(tc["CircuitId"], []).append((key, i))

        # Per-line ordered station list from track 1 (fall back to track 2).
        for code in LINE_ORDER:
            seq = self._routes.get((code, 1)) or self._routes.get((code, 2))
            if not seq:
                continue
            ordered = []
            for tc in seq:
                sc = tc.get("StationCode")
                if sc and sc in self.stations and (not ordered or ordered[-1] != sc):
                    ordered.append(sc)
            if len(ordered) >= 2:
                self.lines.append({
                    "code": code,
                    "color": LINE_HEX[code],
                    "lane": LINE_LANE.get(code, 0.0),
                    "stations": ordered,
                })

    def geometry(self):
        """JSON-serializable static geometry for the frontend."""
        lats = [s["lat"] for s in self.stations.values()]
        lons = [s["lon"] for s in self.stations.values()]
        return {
            "stations": list(self.stations.values()),
            "lines": self.lines,
            "bounds": {
                "latMin": min(lats), "latMax": max(lats),
                "lonMin": min(lons), "lonMax": max(lons),
            },
        }

    # --- live train placement ----------------------------------------------
    def _bracketing_stations(self, key, idx):
        """Nearest station circuit at/before idx and at/after idx on a track."""
        seq = self._routes[key]
        prev = nxt = None
        for j in range(idx, -1, -1):
            if seq[j].get("StationCode"):
                prev = (seq[j]["SeqNum"], seq[j]["StationCode"])
                break
        for j in range(idx, len(seq)):
            if seq[j].get("StationCode"):
                nxt = (seq[j]["SeqNum"], seq[j]["StationCode"])
                break
        return seq[idx]["SeqNum"], prev, nxt

    def place_trains(self, trains):
        dots = []
        for t in trains:
            cid = t.get("CircuitId")
            line = t.get("LineCode")
            direction = t.get("DirectionNum")
            if cid is None or not line:
                continue
            cand = self._circuit_index.get(cid)
            if not cand:
                continue  # yard / pocket track not in standard routes

            # Prefer the route matching this train's line and track (== direction).
            chosen = next((c for c in cand if c[0] == (line, direction)), None)
            chosen = chosen or next((c for c in cand if c[0][0] == line), None) or cand[0]
            key, idx = chosen

            seq_num, prev, nxt = self._bracketing_stations(key, idx)
            point = self._interpolate(seq_num, prev, nxt)
            if point is None:
                continue
            lat, lon, from_code, to_code, frac = point

            dest_code = t.get("DestinationStationCode")
            dots.append({
                "id": t.get("TrainId") or t.get("TrainNumber"),
                "line": line,
                "color": LINE_HEX.get(line, "#9aa"),
                "dir": direction,
                "cars": t.get("CarCount"),
                "dest": self.stations.get(dest_code, {}).get("name", dest_code or "?"),
                "lat": lat,
                "lon": lon,
                "from": from_code,
                "to": to_code,
                "frac": round(frac, 3),
            })
        return dots

    def _interpolate(self, seq_num, prev, nxt):
        # Snap to a single station when only one side is bracketed (terminals).
        if prev and not nxt:
            s = self.stations.get(prev[1])
            return (s["lat"], s["lon"], prev[1], prev[1], 1.0) if s else None
        if nxt and not prev:
            s = self.stations.get(nxt[1])
            return (s["lat"], s["lon"], nxt[1], nxt[1], 0.0) if s else None
        if not prev or not nxt:
            return None

        a = self.stations.get(prev[1])
        b = self.stations.get(nxt[1])
        if not a or not b:
            return None
        if prev[1] == nxt[1] or nxt[0] == prev[0]:
            return (a["lat"], a["lon"], prev[1], nxt[1], 0.0)

        frac = (seq_num - prev[0]) / (nxt[0] - prev[0])
        frac = max(0.0, min(1.0, frac))
        lat = a["lat"] + (b["lat"] - a["lat"]) * frac
        lon = a["lon"] + (b["lon"] - a["lon"]) * frac
        return (lat, lon, prev[1], nxt[1], frac)
