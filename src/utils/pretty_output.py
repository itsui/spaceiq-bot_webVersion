"""
Pretty Terminal Output with Colors

Provides colored, cleaner output for the booking bot.
"""

from colorama import Fore, Back, Style, init
import sys
import os

# Initialize colorama for Windows compatibility
init(autoreset=True)

# Set UTF-8 encoding for Windows console
if os.name == 'nt':  # Windows
    try:
        # Try to set console to UTF-8
        os.system('chcp 65001 >nul 2>&1')
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass


class PrettyOutput:
    """Handles pretty, colored terminal output"""

    # Color shortcuts
    GREEN = Fore.GREEN
    RED = Fore.RED
    YELLOW = Fore.YELLOW
    BLUE = Fore.CYAN
    MAGENTA = Fore.MAGENTA
    WHITE = Fore.WHITE
    GRAY = Fore.LIGHTBLACK_EX
    BOLD = Style.BRIGHT
    RESET = Style.RESET_ALL

    @staticmethod
    def header(text: str, char: str = "="):
        """Print a colored header"""
        line = char * 70
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{line}")
        print(f"{text:^70}")
        print(f"{line}{Style.RESET_ALL}\n")

    @staticmethod
    def success(text: str):
        """Print success message in green"""
        print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")

    @staticmethod
    def error(text: str):
        """Print error message in red"""
        print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")

    @staticmethod
    def warning(text: str):
        """Print warning message in yellow"""
        print(f"{Fore.YELLOW}⚠ {text}{Style.RESET_ALL}")

    @staticmethod
    def info(text: str):
        """Print info message in blue"""
        print(f"{Fore.CYAN}ℹ {text}{Style.RESET_ALL}")

    @staticmethod
    def step(step_num: int, total: int, text: str):
        """Print a step in a process"""
        print(f"{Fore.LIGHTBLACK_EX}[{step_num}/{total}]{Style.RESET_ALL} {text}", end="")
        sys.stdout.flush()

    @staticmethod
    def step_done(success: bool = True):
        """Mark the current step as done"""
        if success:
            print(f" {Fore.GREEN}✓{Style.RESET_ALL}")
        else:
            print(f" {Fore.RED}✗{Style.RESET_ALL}")

    @staticmethod
    def date_header(date: str, date_num: int, total_dates: int):
        """Print a date being processed"""
        print(f"\n{Fore.MAGENTA}{Style.BRIGHT}[{date_num}/{total_dates}] {date}{Style.RESET_ALL}")

    @staticmethod
    def booking_result(date: str, success: bool, desk_code: str = None):
        """Print booking result for a date"""
        if success:
            desk_info = f" ({desk_code})" if desk_code else ""
            print(f"{Fore.GREEN}{Style.BRIGHT}✓ BOOKED{Style.RESET_ALL} {date}{Fore.GREEN}{desk_info}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}○ SKIPPED{Style.RESET_ALL} {date} {Fore.LIGHTBLACK_EX}(no available desks){Style.RESET_ALL}")

    @staticmethod
    def summary_table(results: dict, existing_bookings: list = None):
        """Print a summary table of all results"""
        booked = [date for date, success in results.items() if success]
        skipped = [date for date, success in results.items() if not success]

        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'SUMMARY':^70}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}")

        if existing_bookings:
            print(f"{Fore.GREEN}Already Booked:{Style.RESET_ALL} {len(existing_bookings)} dates")
            for date in sorted(existing_bookings):
                print(f"  {Fore.GREEN}✓{Style.RESET_ALL} {date}")
            print()

        if booked:
            print(f"{Fore.GREEN}Newly Booked:{Style.RESET_ALL} {len(booked)} dates")
            for date in sorted(booked):
                print(f"  {Fore.GREEN}✓{Style.RESET_ALL} {date}")
        else:
            print(f"{Fore.YELLOW}Newly Booked:{Style.RESET_ALL} 0 dates")

        if skipped:
            print(f"\n{Fore.YELLOW}Skipped:{Style.RESET_ALL} {len(skipped)} dates {Fore.LIGHTBLACK_EX}(no seats available){Style.RESET_ALL}")
            for date in sorted(skipped):
                print(f"  {Fore.LIGHTBLACK_EX}○ {date}{Style.RESET_ALL}")

        print(f"{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}\n")

    @staticmethod
    def round_header(round_num: int, dates_count: int, existing_count: int = 0):
        """Print round header for continuous loop mode"""
        print(f"\n{Fore.MAGENTA}{Style.BRIGHT}{'=' * 70}")
        print(f"ROUND {round_num}".center(70))
        print(f"{'=' * 70}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Trying {dates_count} date(s)", end="")
        if existing_count > 0:
            print(f" • Skipping {existing_count} already booked", end="")
        print(f"{Style.RESET_ALL}\n")

    @staticmethod
    def waiting(seconds: int, reason: str = "No seats available"):
        """Print waiting message"""
        print(f"\n{Fore.YELLOW}⏳ {reason} • Waiting {seconds}s before retry...{Style.RESET_ALL}")

    @staticmethod
    def mode_banner(mode: str):
        """Print mode banner"""
        banners = {
            "headless": (
                f"{Fore.BLUE}{Style.BRIGHT}HEADLESS MODE{Style.RESET_ALL}",
                f"{Fore.LIGHTBLACK_EX}Background operation • Checks existing bookings • Continuous loop • Ctrl+C to stop{Style.RESET_ALL}"
            ),
            "loop": (
                f"{Fore.MAGENTA}{Style.BRIGHT}CONTINUOUS LOOP MODE{Style.RESET_ALL}",
                f"{Fore.YELLOW}Keeps trying all dates forever • Press Ctrl+C to stop{Style.RESET_ALL}"
            ),
            "poll": (
                f"{Fore.CYAN}{Style.BRIGHT}POLLING MODE{Style.RESET_ALL}",
                f"{Fore.YELLOW}Keeps trying until at least one booking succeeds{Style.RESET_ALL}"
            )
        }

        if mode in banners:
            title, desc = banners[mode]
            print(f"\n{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}")
            print(f"{title}")
            print(f"{desc}")
            print(f"{Fore.CYAN}{'─' * 70}{Style.RESET_ALL}\n")

    @staticmethod
    def progress_inline(text: str):
        """Print inline progress (same line, no newline)"""
        print(f"\r{Fore.LIGHTBLACK_EX}{text}{Style.RESET_ALL}", end="")
        sys.stdout.flush()

    @staticmethod
    def clear_line():
        """Clear the current line"""
        print("\r" + " " * 80 + "\r", end="")
        sys.stdout.flush()


# Convenience functions
def header(text: str, char: str = "="):
    PrettyOutput.header(text, char)

def success(text: str):
    PrettyOutput.success(text)

def error(text: str):
    PrettyOutput.error(text)

def warning(text: str):
    PrettyOutput.warning(text)

def info(text: str):
    PrettyOutput.info(text)
