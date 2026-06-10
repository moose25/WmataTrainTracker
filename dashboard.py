"""Live WMATA terminal dashboard.

Pulls real-time rail predictions, service incidents, and elevator/escalator
outages together into one refreshing view. Optionally adds bus predictions for
a given stop. Built on the shared WmataClient (see wmata.py).

Examples:
    python dashboard.py
    python dashboard.py --stations A01,C01,B01 --interval 15
    python dashboard.py --bus-stop 1001195
"""

import argparse
import os
import time

from colorama import Fore, Style, init as colorama_init

from wmata import WmataClient, WmataError
from colors import get_line_color, tag

colorama_init()

# A few central, busy stations as a sensible default.
DEFAULT_STATIONS = ["A01", "C01", "B01"]  # Metro Center (RD), Metro Center (BL/OR/SV), Gallery Pl (RD)


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def header(text):
    bar = "=" * 80
    return f"{Style.BRIGHT}{bar}\n{text}\n{bar}{Style.RESET_ALL}"


def section(text):
    return f"\n{Style.BRIGHT}{Fore.CYAN}{text}{Style.RESET_ALL}\n{'-' * 80}"


def render_predictions(client, station_codes):
    lines = [section("RAIL PREDICTIONS")]
    trains = client.rail_predictions(",".join(station_codes))
    if not trains:
        lines.append(f"{Fore.MAGENTA}No predictions reported.{Style.RESET_ALL}")
        return "\n".join(lines)

    # Group by station for readability.
    by_station = {}
    for t in trains:
        by_station.setdefault(t.get("LocationName", t.get("LocationCode", "?")), []).append(t)

    for station_name, station_trains in by_station.items():
        lines.append(f"{Style.BRIGHT}{station_name}{Style.RESET_ALL}")
        for t in station_trains:
            line_code = t.get("Line", "--")
            dest = t.get("DestinationName", t.get("Destination", "?"))
            mins = t.get("Min", "?")
            cars = t.get("Car") or "-"
            if dest == "No Passenger":
                color = Fore.MAGENTA
                mins_str = f"{color}{str(mins):>5}{Style.RESET_ALL}"
            else:
                color = get_line_color(line_code)
                mins_str = f"{color}{str(mins):>5}{Style.RESET_ALL}"
            lines.append(
                f"  {tag(line_code)}  {dest:<28} {mins_str} min   {cars}-car"
            )
        lines.append("")
    return "\n".join(lines)


def render_bus(client, stop_id):
    lines = [section(f"BUS PREDICTIONS - stop {stop_id}")]
    data = client.bus_predictions(stop_id)
    stop_name = data.get("StopName", "")
    if stop_name:
        lines.append(f"{Style.BRIGHT}{stop_name}{Style.RESET_ALL}")
    preds = data.get("Predictions", [])
    if not preds:
        lines.append(f"{Fore.MAGENTA}No bus predictions.{Style.RESET_ALL}")
        return "\n".join(lines)
    for p in preds:
        route = p.get("RouteID", "?")
        direction = p.get("DirectionText", "")
        mins = p.get("Minutes", "?")
        lines.append(f"  {Fore.GREEN}[{route}]{Style.RESET_ALL} {direction:<28} {str(mins):>3} min")
    return "\n".join(lines)


def render_incidents(client):
    lines = [section("RAIL INCIDENTS")]
    incidents = client.rail_incidents()
    if not incidents:
        lines.append(f"{Fore.GREEN}No reported rail incidents.{Style.RESET_ALL}")
    for inc in incidents:
        affected = inc.get("LinesAffected", "").replace(";", " ").split()
        tags = " ".join(tag(code) for code in affected if code)
        lines.append(f"  {tags} {Fore.YELLOW}{inc.get('IncidentType', '')}{Style.RESET_ALL}")
        lines.append(f"    {inc.get('Description', '')}")
    return "\n".join(lines)


def render_elevator(client):
    lines = [section("ELEVATOR / ESCALATOR OUTAGES")]
    outages = client.elevator_incidents()
    if not outages:
        lines.append(f"{Fore.GREEN}No reported outages.{Style.RESET_ALL}")
    for o in outages:
        unit = o.get("UnitType", "UNIT")
        station = o.get("StationName", "")
        symptom = o.get("SymptomDescription", "")
        lines.append(
            f"  {Fore.RED}{unit}{Style.RESET_ALL} @ {Style.BRIGHT}{station}{Style.RESET_ALL} - {symptom}"
        )
    return "\n".join(lines)


def parse_args():
    p = argparse.ArgumentParser(description="Live WMATA terminal dashboard")
    p.add_argument(
        "--stations",
        default=",".join(DEFAULT_STATIONS),
        help="Comma-separated rail station codes (default: central stations)",
    )
    p.add_argument("--bus-stop", dest="bus_stop", help="Optional 7-digit bus StopID to track")
    p.add_argument("--interval", type=int, default=20, help="Refresh interval in seconds")
    return p.parse_args()


def main():
    args = parse_args()
    client = WmataClient()
    station_codes = [s.strip() for s in args.stations.split(",") if s.strip()]

    while True:
        clear()
        print(header("WMATA LIVE DASHBOARD"))
        print(render_predictions(client, station_codes))
        if args.bus_stop:
            print(render_bus(client, args.bus_stop))
        print(render_incidents(client))
        print(render_elevator(client))
        print(f"\n{Style.DIM}Refreshing every {args.interval}s — Ctrl+C to quit{Style.RESET_ALL}")
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except WmataError as exc:
        raise SystemExit(str(exc))
    except KeyboardInterrupt:
        pass
