"""Original train tracker: lists every rail station with its supported lines
and the next few trains, refreshing every 20 seconds.

Now built on the shared WmataClient (see wmata.py)."""

import time

from colorama import Fore, Style

from wmata import WmataClient, WmataError
from colors import get_line_color

client = WmataClient()


# Station information
def display_station_information(stations):
    print("Station Information:")
    for station in stations:
        line_support = get_line_support(station)
        station_code = station["Code"]
        next_trains = client.rail_predictions(station_code)[:3]

        print(f"{line_support}")
        if next_trains:
            display_next_trains(next_trains)
        else:
            print(f"{Fore.MAGENTA}No scheduled trains{Style.RESET_ALL}")

        print()


# Grabbing information about stations
def get_line_support(station):
    station_name = station["Name"]
    line_codes = station["LineCode1"], station["LineCode2"], station["LineCode3"], station["LineCode4"]
    line_support = f"{station_name:<25} {' '.join([f'{get_line_color(line_code)}[{line_code}]{Style.RESET_ALL}' for line_code in line_codes if line_code])}"
    return line_support


# Print and format the output of the trains
def display_next_trains(next_trains):
    dashed_line = "_" * 80

    if not next_trains:
        print(f"{Fore.MAGENTA}No scheduled trains.{Style.RESET_ALL}")

    for i, train in enumerate(next_trains):
        line_code = train["Line"]
        destination = train["Destination"]
        arrival_time = train["Min"]

        if destination == "No Passenger":
            color = Fore.MAGENTA
            destination = f"{Style.BRIGHT}{destination}{Style.RESET_ALL}"
            arrival_time = f"{Fore.MAGENTA}{arrival_time:>5}{Style.RESET_ALL}"
        else:
            color = get_line_color(line_code)
            arrival_time = f"{color}{arrival_time:>5}{Style.RESET_ALL}"

        train_line = f"{color}[{line_code}]{Style.RESET_ALL}"
        train_info = f"{train_line}  Destination: {destination}\t\tMinutes: {arrival_time}"
        print(train_info)

    print(dashed_line)


def abbreviate_destination(destination):
    if len(destination) > 20 and len(destination[:18]) + 2 < 21:
        destination = f"{destination[:18]}.."
    return destination


def main():
    stations = client.rail_stations()
    # Delay for 20 seconds before the next update
    while True:
        display_station_information(stations)
        time.sleep(20)


if __name__ == "__main__":
    try:
        main()
    except WmataError as exc:
        raise SystemExit(str(exc))
    except KeyboardInterrupt:
        pass
