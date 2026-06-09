# DC Metro Train Tracker

Python project to track the DC Metro (WMATA) in real time from your terminal —
rail stations and the lines they support, upcoming train arrivals, bus
predictions, service incidents, and elevator/escalator outages. The original
fun project now sits on a reusable WMATA API client.

## Setup

1. Get a free API key from WMATA: https://developer.wmata.com/
2. Copy `.env.example` to `.env` and paste your key:

   ```
   WMATA_API_KEY=your_key_here
   ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

## Usage

**Original station list** (every station, supported lines, next 3 trains, refreshing every 20s):

```
python stationSchedule.py
```

**Live dashboard** (rail predictions + incidents + elevator/escalator outages, optional bus stop):

```
python dashboard.py
python dashboard.py --stations A01,C01,B01 --interval 15
python dashboard.py --bus-stop 1001195
```

## API client (`wmata.py`)

`WmataClient` wraps the WMATA **JSON REST** endpoints — use it to build your own
tools:

```python
from wmata import WmataClient

client = WmataClient()                 # reads WMATA_API_KEY from .env
trains = client.rail_predictions("A01")
buses = client.bus_predictions("1001195")
incidents = client.rail_incidents()
positions = client.train_positions()
```

Covered endpoint groups:

- **Rail Station Information** — lines, stations, station info, entrances, parking, times, path, fares (`station_to_station`)
- **Real-Time Rail Predictions** — `rail_predictions`
- **Train Positions** — `train_positions`, `standard_routes`, `track_circuits`
- **Bus Route and Stop Methods** — `bus_routes`, `bus_route_details`, `bus_route_schedule`, `bus_stops`, `bus_stop_schedule`, `bus_positions`
- **Real-Time Bus Predictions** — `bus_predictions`
- **Incidents** — `rail_incidents`, `bus_incidents`, `elevator_incidents`
- **Misc Methods** — call via the generic `client.get("/path", params)` passthrough

> GTFS / GTFS-RT (protobuf) feeds are not covered yet. The generic `get()` method
> can reach any other JSON endpoint not given a dedicated wrapper.

## Files

- `wmata.py` — reusable API client
- `colors.py` — shared colorama line-color helpers
- `stationSchedule.py` — original refreshing station list
- `dashboard.py` — live multi-panel terminal dashboard

## Screenshots

![Screenshot 2023-05-18 at 6 20 41 PM](https://github.com/moose25/WmataTrainTracker/assets/25665535/3b4a42bc-7a5e-4d90-85a4-cc49986be439)

![Screenshot 2023-05-18 at 6 21 24 PM](https://github.com/moose25/WmataTrainTracker/assets/25665535/00e5945c-284f-45a0-82fe-3b8766475714)

Minor error handling for stations under construction or other events that show no trains on their schedule.
![Screenshot 2023-05-18 at 6 21 44 PM](https://github.com/moose25/WmataTrainTracker/assets/25665535/a13886ed-bc77-43d9-8804-71fa1f43faa4)
