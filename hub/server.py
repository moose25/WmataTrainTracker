"""Flask backend for the WMATA live hub.

Serves the static frontend plus JSON endpoints built on the shared WmataClient:
  GET /                  -> the hub page
  GET /api/geometry      -> static diagram (stations + line polylines + bounds)
  GET /api/trains        -> live train dots (interpolated lat/lon), cached briefly
  GET /api/arrivals      -> next-train predictions for ?codes=A01,C01
  GET /api/incidents     -> rail incidents + elevator/escalator outages

Run from the project root:  python hub/server.py
"""

import os
import sys
import time

from flask import Flask, jsonify, request, send_from_directory

# Make the parent project (wmata.py) importable when run as `python hub/server.py`.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from wmata import WmataClient, WmataError  # noqa: E402
from geometry import Diagram  # noqa: E402

app = Flask(__name__, static_folder=os.path.join(HERE, "static"), static_url_path="")

client = WmataClient()
diagram = Diagram(client)


class TTLCache:
    """Tiny single-value cache so multiple browser polls share one API call."""

    def __init__(self, ttl, fetch):
        self.ttl = ttl
        self.fetch = fetch
        self._value = None
        self._at = 0.0

    def get(self):
        now = time.monotonic()
        if self._value is None or now - self._at > self.ttl:
            self._value = self.fetch()
            self._at = now
        return self._value


trains_cache = TTLCache(8, lambda: diagram.place_trains(client.train_positions()))
incidents_cache = TTLCache(
    30,
    lambda: {
        "rail": client.rail_incidents(),
        "elevator": client.elevator_incidents(),
    },
)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/geometry")
def api_geometry():
    return jsonify(diagram.geometry())


@app.route("/api/trains")
def api_trains():
    return jsonify({"trains": trains_cache.get()})


@app.route("/api/arrivals")
def api_arrivals():
    codes = request.args.get("codes", "")
    codes = [c.strip() for c in codes.split(",") if c.strip()]
    if not codes:
        return jsonify({"stations": []})

    trains = client.rail_predictions(",".join(codes))
    by_station = {}
    for t in trains:
        name = t.get("LocationName") or t.get("LocationCode")
        by_station.setdefault(name, []).append({
            "line": t.get("Line"),
            "dest": t.get("DestinationName") or t.get("Destination"),
            "min": t.get("Min"),
            "cars": t.get("Car"),
            "group": t.get("Group"),
        })
    stations = [{"name": name, "trains": trains_} for name, trains_ in by_station.items()]
    return jsonify({"stations": stations})


@app.route("/api/incidents")
def api_incidents():
    data = incidents_cache.get()
    rail = [{
        "lines": [c for c in (i.get("LinesAffected") or "").replace(";", " ").split() if c],
        "type": i.get("IncidentType"),
        "description": i.get("Description"),
    } for i in data["rail"]]
    elevator = [{
        "unit": e.get("UnitType"),
        "station": e.get("StationName"),
        "symptom": e.get("SymptomDescription"),
    } for e in data["elevator"]]
    return jsonify({"rail": rail, "elevator": elevator})


def main():
    port = int(os.environ.get("PORT", "5000"))
    print(f"WMATA hub running at http://127.0.0.1:{port}  (Ctrl+C to quit)")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    try:
        main()
    except WmataError as exc:
        raise SystemExit(str(exc))
