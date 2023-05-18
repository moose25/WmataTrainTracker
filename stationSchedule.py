import requests
from colorama import Fore, Style
import time

def get_station_information():
    stations_url = "https://api.wmata.com/Rail.svc/json/jStations"
    headers = {"api_key": "{YOUR_API_KEY}"} # CHANGE THIS TO YOUR API KEY

    response = requests.get(stations_url, headers=headers)
    data = response.json()

    stations = data["Stations"]
    return stations

# API for train station incoming train predictions
def get_next_trains(station_code):
    predictions_url = f"https://api.wmata.com/StationPrediction.svc/json/GetPrediction/{station_code}"
    headers = {"api_key": "{YOUR_API_KEY}"} # CHANGE THIS TO YOUR API KEY

    response = requests.get(predictions_url, headers=headers)
    data = response.json()

    if "Trains" in data:
        predictions = data["Trains"][:3]
    else:
        predictions = []

    return predictions

# Station information
def display_station_information(stations):
    print("Station Information:")
    for station in stations:
        line_support = get_line_support(station)
        station_code = station["Code"]
        next_trains = get_next_trains(station_code)

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

# Color the line code the color of the train line
def get_line_color(line_code):
    line_colors = {
        "RD": Fore.RED,
        "BL": Fore.BLUE,
        "YL": Fore.LIGHTYELLOW_EX,
        "OR": Fore.YELLOW,
        "GR": Fore.GREEN,
        "SV": Fore.LIGHTBLACK_EX,
    }

    return line_colors.get(line_code, Fore.LIGHTGREEN_EX)

def abbreviate_destination(destination):
    if len(destination) > 20 and len(destination[:18]) + 2 < 21:
        destination = f"{destination[:18]}.."
    return destination

stations = get_station_information()

# Delay for 20 seconds before the next update
while True:
    display_station_information(stations)
    time.sleep(20)  
