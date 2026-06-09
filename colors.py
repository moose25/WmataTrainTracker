"""Shared colorama helpers for WMATA line colors."""

from colorama import Fore, Style

LINE_COLORS = {
    "RD": Fore.RED,
    "BL": Fore.BLUE,
    "YL": Fore.LIGHTYELLOW_EX,
    "OR": Fore.YELLOW,
    "GR": Fore.GREEN,
    "SV": Fore.LIGHTBLACK_EX,
}


def get_line_color(line_code):
    return LINE_COLORS.get(line_code, Fore.LIGHTGREEN_EX)


def tag(line_code):
    """A colored ``[XX]`` line tag, reset afterward."""
    return f"{get_line_color(line_code)}[{line_code}]{Style.RESET_ALL}"
