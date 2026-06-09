"""Thin Python client for the WMATA (DC Metro) JSON REST APIs.

Covers the JSON endpoints from the WMATA developer portal:
  - Rail Station Information
  - Real-Time Rail Predictions
  - Train Positions
  - Bus Route and Stop Methods
  - Real-Time Bus Predictions
  - Incidents (rail / bus / elevator)
  - Misc Methods (via the generic ``get`` passthrough)

GTFS / GTFS-RT (protobuf) feeds are intentionally not covered here.

Usage:
    from wmata import WmataClient
    client = WmataClient()              # reads WMATA_API_KEY from the environment / .env
    stations = client.rail_stations()
    trains = client.rail_predictions("A01")
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.wmata.com"


class WmataError(RuntimeError):
    """Raised when the WMATA API returns an error or no key is configured."""


class WmataClient:
    def __init__(self, api_key: str | None = None, timeout: int = 15):
        self.api_key = api_key or os.getenv("WMATA_API_KEY")
        if not self.api_key:
            raise WmataError(
                "Missing WMATA_API_KEY. Copy .env.example to .env and paste your "
                "free key from https://developer.wmata.com/"
            )
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"api_key": self.api_key})

    # --- core ---------------------------------------------------------------
    def get(self, path: str, params: dict | None = None) -> dict:
        """Generic GET against any WMATA endpoint.

        ``path`` is appended to the base URL, e.g. "/Rail.svc/json/jStations".
        Use this for endpoints not given a dedicated method below (e.g. Misc).
        """
        url = f"{BASE_URL}{path}"
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise WmataError(f"WMATA request failed for {path}: {exc}") from exc
        return resp.json()

    # --- Rail Station Information -------------------------------------------
    def rail_lines(self) -> list:
        return self.get("/Rail.svc/json/jLines").get("Lines", [])

    def rail_stations(self, line_code: str | None = None) -> list:
        params = {"LineCode": line_code} if line_code else None
        return self.get("/Rail.svc/json/jStations", params).get("Stations", [])

    def station_info(self, station_code: str) -> dict:
        return self.get("/Rail.svc/json/jStationInfo", {"StationCode": station_code})

    def station_entrances(self, lat: float | None = None, lon: float | None = None,
                          radius: float | None = None) -> list:
        params = {}
        if lat is not None and lon is not None and radius is not None:
            params = {"Lat": lat, "Lon": lon, "Radius": radius}
        return self.get("/Rail.svc/json/jStationEntrances", params or None).get("Entrances", [])

    def station_parking(self, station_code: str) -> list:
        return self.get(
            "/Rail.svc/json/jStationParkingInfo", {"StationCode": station_code}
        ).get("StationsParking", [])

    def station_times(self, station_code: str) -> list:
        return self.get(
            "/Rail.svc/json/jStationTimes", {"StationCode": station_code}
        ).get("StationTimes", [])

    def path_between(self, from_station: str, to_station: str) -> list:
        params = {"FromStationCode": from_station, "ToStationCode": to_station}
        return self.get("/Rail.svc/json/jPath", params).get("Path", [])

    def station_to_station(self, from_station: str | None = None,
                           to_station: str | None = None) -> list:
        """Fares and travel times between stations (omit args for all pairs)."""
        params = {}
        if from_station:
            params["FromStationCode"] = from_station
        if to_station:
            params["ToStationCode"] = to_station
        return self.get(
            "/Rail.svc/json/jSrcStationToDstStationInfo", params or None
        ).get("StationToStationInfos", [])

    # --- Real-Time Rail Predictions ----------------------------------------
    def rail_predictions(self, station_codes: str = "All") -> list:
        """Next-train predictions. ``station_codes`` may be one code, several
        comma-separated codes, or "All"."""
        return self.get(
            f"/StationPrediction.svc/json/GetPrediction/{station_codes}"
        ).get("Trains", [])

    # --- Train Positions ----------------------------------------------------
    def train_positions(self) -> list:
        return self.get(
            "/TrainPositions/TrainPositions", {"contentType": "json"}
        ).get("TrainPositions", [])

    def standard_routes(self) -> list:
        return self.get(
            "/TrainPositions/StandardRoutes", {"contentType": "json"}
        ).get("StandardRoutes", [])

    def track_circuits(self) -> list:
        return self.get(
            "/TrainPositions/TrackCircuits", {"contentType": "json"}
        ).get("TrackCircuits", [])

    # --- Bus Route and Stop Methods ----------------------------------------
    def bus_routes(self) -> list:
        return self.get("/Bus.svc/json/jRoutes").get("Routes", [])

    def bus_route_details(self, route_id: str, date: str | None = None) -> dict:
        params = {"RouteID": route_id}
        if date:
            params["Date"] = date
        return self.get("/Bus.svc/json/jRouteDetails", params)

    def bus_route_schedule(self, route_id: str, date: str | None = None,
                           including_variations: bool = False) -> dict:
        params = {"RouteID": route_id, "IncludingVariations": including_variations}
        if date:
            params["Date"] = date
        return self.get("/Bus.svc/json/jRouteSchedule", params)

    def bus_stops(self, lat: float | None = None, lon: float | None = None,
                  radius: float | None = None) -> list:
        params = {}
        if lat is not None and lon is not None and radius is not None:
            params = {"Lat": lat, "Lon": lon, "Radius": radius}
        return self.get("/Bus.svc/json/jStops", params or None).get("Stops", [])

    def bus_stop_schedule(self, stop_id: str, date: str | None = None) -> dict:
        params = {"StopID": stop_id}
        if date:
            params["Date"] = date
        return self.get("/Bus.svc/json/jStopSchedule", params)

    def bus_positions(self, route_id: str | None = None, lat: float | None = None,
                      lon: float | None = None, radius: float | None = None) -> list:
        params = {}
        if route_id:
            params["RouteID"] = route_id
        if lat is not None and lon is not None and radius is not None:
            params.update({"Lat": lat, "Lon": lon, "Radius": radius})
        return self.get("/Bus.svc/json/jBusPositions", params or None).get("BusPositions", [])

    # --- Real-Time Bus Predictions -----------------------------------------
    def bus_predictions(self, stop_id: str) -> dict:
        return self.get("/NextBusService.svc/json/jPredictions", {"StopID": stop_id})

    # --- Incidents ----------------------------------------------------------
    def rail_incidents(self) -> list:
        return self.get("/Incidents.svc/json/Incidents").get("Incidents", [])

    def bus_incidents(self) -> list:
        return self.get("/Incidents.svc/json/BusIncidents").get("BusIncidents", [])

    def elevator_incidents(self) -> list:
        return self.get("/Incidents.svc/json/ElevatorIncidents").get(
            "ElevatorIncidents", []
        )
