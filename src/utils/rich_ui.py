"""
Rich Terminal UI for SpaceIQ Booking Bot

Beautiful terminal interface with panels, progress bars, and live updates.
Inspired by CyberDropDownloader's clean UI design.
"""

from typing import Dict, List, Optional
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn
from rich.text import Text
from rich.align import Align
from rich import box
from enum import Enum
import time


class DateStatus(Enum):
    """Status of a booking date"""
    PENDING = "pending"
    TRYING = "trying"
    SUCCESS = "success"
    SKIPPED = "skipped"
    ALREADY_BOOKED = "already_booked"
    FAILED = "failed"


class RichUI:
    """
    Beautiful Rich-based terminal UI for booking operations.

    Features:
    - Live updating panels for statistics
    - Progress bars for booking operations
    - Color-coded status messages
    - Clean, organized layout
    """

    def __init__(self):
        self.console = Console(force_terminal=True, legacy_windows=False)
        self.stats = {
            "completed": 0,
            "already_booked": 0,
            "skipped": 0,
            "failed": 0,
            "total": 0
        }
        self.current_round = 1
        self.dates_tried = []
        self.successful_bookings = []
        self.failed_dates = []
        self.existing_bookings = []
        self.current_operation = ""
        self.current_step = ""
        self.start_time = time.time()

        # Date tracking with status and desk info
        self.date_statuses: Dict[str, DateStatus] = {}
        self.date_desks: Dict[str, str] = {}  # Maps date -> desk code
        self.date_attempts: Dict[str, int] = {}  # Maps date -> attempt count

        # Live dashboard
        self.live_dashboard = None
        self.layout = None

        # Activity log for detailed operations
        self.activity_log: List[str] = []
        self.max_activity_log = 15  # Keep last 15 activity messages

        # Countdown timer
        self.countdown_seconds = 0
        self.countdown_message = ""

    def clear(self):
        """Clear the console"""
        self.console.clear()

    def get_dates_status_panel(self) -> Panel:
        """
        Create a panel showing all dates with their current status.
        Color-coded for easy visualization.
        """
        if not self.date_statuses:
            content = Text("No dates loaded yet...", style="dim")
        else:
            table = Table.grid(padding=(0, 2))
            table.add_column(style="bold", justify="left", width=16)
            table.add_column(justify="left", width=20)
            table.add_column(justify="left", style="dim")

            # Sort dates chronologically
            sorted_dates = sorted(self.date_statuses.keys())

            for date in sorted_dates:
                status = self.date_statuses[date]
                desk = self.date_desks.get(date, "")
                attempts = self.date_attempts.get(date, 0)

                # Status icon and color
                if status == DateStatus.SUCCESS:
                    icon = "[green][+][/green]"
                    status_text = f"[green]BOOKED[/green]"
                    detail = f"[green]{desk}[/green]" if desk else ""
                elif status == DateStatus.ALREADY_BOOKED:
                    icon = "[cyan][=][/cyan]"
                    status_text = f"[cyan]ALREADY BOOKED[/cyan]"
                    detail = ""
                elif status == DateStatus.TRYING:
                    icon = "[yellow][>][/yellow]"
                    status_text = f"[yellow]TRYING[/yellow]"
                    detail = f"[dim]attempt {attempts}[/dim]" if attempts > 0 else ""
                elif status == DateStatus.SKIPPED:
                    icon = "[yellow][-][/yellow]"
                    status_text = f"[yellow]NO SEATS[/yellow]"
                    detail = ""
                elif status == DateStatus.FAILED:
                    icon = "[red][!][/red]"
                    status_text = f"[red]FAILED[/red]"
                    detail = ""
                else:  # PENDING
                    icon = "[dim][ ][/dim]"
                    status_text = f"[dim]PENDING[/dim]"
                    detail = ""

                table.add_row(f"{icon} {date}", status_text, detail)

            content = table

        return Panel(
            content,
            title="[bold cyan]Booking Dates Status[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED
        )

    def get_stats_panel(self) -> Panel:
        """
        Create a statistics panel showing booking results.
        Similar to the 'Files' panel in CyberDropDownloader.
        """
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold", justify="left")
        table.add_column(justify="right", style="bold")
        table.add_column(justify="right")

        total = self.stats["total"] if self.stats["total"] > 0 else 1

        # Completed bookings (green)
        completed_pct = (self.stats["completed"] / total) * 100
        table.add_row(
            "[green]Completed[/green]",
            f"[green]{completed_pct:.1f}%[/green]",
            f"[dim]{self.stats['completed']} of {self.stats['total']} Dates[/dim]"
        )

        # Already booked (cyan)
        already_pct = (self.stats["already_booked"] / total) * 100
        table.add_row(
            "[cyan]Already Booked[/cyan]",
            f"[cyan]{already_pct:.1f}%[/cyan]",
            f"[dim]{self.stats['already_booked']} of {self.stats['total']} Dates[/dim]"
        )

        # Skipped (yellow)
        skipped_pct = (self.stats["skipped"] / total) * 100
        table.add_row(
            "[yellow]No Seats Available[/yellow]",
            f"[yellow]{skipped_pct:.1f}%[/yellow]",
            f"[dim]{self.stats['skipped']} of {self.stats['total']} Dates[/dim]"
        )

        # Failed (red)
        failed_pct = (self.stats["failed"] / total) * 100
        table.add_row(
            "[red]Failed[/red]",
            f"[red]{failed_pct:.1f}%[/red]",
            f"[dim]{self.stats['failed']} of {self.stats['total']} Dates[/dim]"
        )

        return Panel(
            table,
            title="[bold cyan]Booking Statistics[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED
        )

    def get_current_operation_panel(self) -> Panel:
        """
        Create a panel showing current operations with countdown.
        Similar to the 'Scraping' panel in CyberDropDownloader.
        """
        lines = []

        if self.current_operation:
            lines.append(Text("> ", style="yellow bold") + Text(self.current_operation, style="white"))

        if self.current_step:
            lines.append(Text("  ", style="dim") + Text(self.current_step, style="dim"))

        # Show countdown if active
        if self.countdown_seconds > 0:
            mins = self.countdown_seconds // 60
            secs = self.countdown_seconds % 60
            countdown_text = f"{mins:02d}:{secs:02d}"
            lines.append(Text(f"\n  Countdown: ", style="dim") + Text(countdown_text, style="yellow bold"))

        if not lines:
            content = Text("Idle...", style="dim")
        else:
            content = Text("\n").join(lines)

        return Panel(
            Align.left(content),
            title="[bold yellow]Current Activity[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED
        )

    def get_activity_log_panel(self) -> Panel:
        """
        Create a panel showing detailed activity log.
        Shows last 15 operations for debugging/monitoring.
        """
        if not self.activity_log:
            content = Text("No activity yet...", style="dim")
        else:
            # Show last entries (most recent at bottom)
            recent_logs = self.activity_log[-self.max_activity_log:]
            log_lines = []
            for log in recent_logs:
                # Add timestamp-style prefix
                log_lines.append(Text(log, style="dim"))

            content = Text("\n").join(log_lines)

        return Panel(
            Align.left(content),
            title="[bold blue]Activity Log[/bold blue]",
            border_style="blue",
            box=box.ROUNDED
        )

    def get_round_info_panel(self) -> Panel:
        """
        Create a panel showing round information.
        """
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold cyan", justify="left")
        table.add_column(justify="left", style="white")

        # Runtime
        runtime = time.time() - self.start_time
        hours = int(runtime // 3600)
        minutes = int((runtime % 3600) // 60)
        seconds = int(runtime % 60)
        runtime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Calculate pending/trying dates
        pending = sum(1 for s in self.date_statuses.values() if s in [DateStatus.PENDING, DateStatus.TRYING, DateStatus.SKIPPED])
        total = len(self.date_statuses)

        table.add_row("Round:", f"#{self.current_round}")
        table.add_row("Runtime:", runtime_str)
        table.add_row("Dates:", f"{pending}/{total} remaining")

        # Next wait time based on round
        if self.current_round <= 5:
            next_wait = "1 min"
        elif self.current_round <= 15:
            next_wait = "5 min"
        else:
            next_wait = "15 min"
        table.add_row("Next Check:", next_wait)

        return Panel(
            table,
            title="[bold magenta]Session Info[/bold magenta]",
            border_style="magenta",
            box=box.ROUNDED
        )

    def get_summary_panel(self) -> Panel:
        """
        Create a quick summary panel showing key metrics.
        """
        # Count statuses
        success_count = sum(1 for s in self.date_statuses.values() if s == DateStatus.SUCCESS)
        already_count = sum(1 for s in self.date_statuses.values() if s == DateStatus.ALREADY_BOOKED)
        skipped_count = sum(1 for s in self.date_statuses.values() if s == DateStatus.SKIPPED)
        trying_count = sum(1 for s in self.date_statuses.values() if s == DateStatus.TRYING)
        pending_count = sum(1 for s in self.date_statuses.values() if s == DateStatus.PENDING)

        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold", justify="left")
        table.add_column(justify="right", style="bold")

        if success_count > 0:
            table.add_row("[green]Newly Booked[/green]", f"[green]{success_count}[/green]")
        if already_count > 0:
            table.add_row("[cyan]Already Booked[/cyan]", f"[cyan]{already_count}[/cyan]")
        if trying_count > 0:
            table.add_row("[yellow]Trying Now[/yellow]", f"[yellow]{trying_count}[/yellow]")
        if skipped_count > 0:
            table.add_row("[yellow]No Seats[/yellow]", f"[yellow]{skipped_count}[/yellow]")
        if pending_count > 0:
            table.add_row("[dim]Pending[/dim]", f"[dim]{pending_count}[/dim]")

        if not table.row_count:
            content = Text("No data yet...", style="dim")
        else:
            content = table

        return Panel(
            content,
            title="[bold green]Quick Summary[/bold green]",
            border_style="green",
            box=box.ROUNDED
        )

    def create_layout(self) -> Layout:
        """
        Create the main layout with all panels.

        Layout structure:
        +------------------+------------------+
        |      Header (full width)           |
        +------------------+------------------+
        | Dates Status     | Session Info     |
        |                  +------------------+
        |                  | Summary          |
        |                  +------------------+
        |                  | Current Activity |
        +------------------+------------------+
        |      Activity Log (full width)     |
        +------------------+------------------+
        """
        layout = Layout()

        # Create header
        header = Panel(
            Align.center(
                Text("SpaceIQ Multi-Date Booking Bot", style="bold cyan"),
            ),
            style="bold white on blue",
            box=box.DOUBLE
        )

        # Split layout
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=18)
        )

        layout["header"].update(header)

        # Split body into two columns
        layout["body"].split_row(
            Layout(name="left", ratio=3),
            Layout(name="right", ratio=2)
        )

        # Right column: Session Info, Summary, and Current Activity
        layout["right"].split(
            Layout(name="session_info", size=10),
            Layout(name="summary", size=10),
            Layout(name="current_op")
        )

        # Update panels
        layout["left"].update(self.get_dates_status_panel())
        layout["session_info"].update(self.get_round_info_panel())
        layout["summary"].update(self.get_summary_panel())
        layout["current_op"].update(self.get_current_operation_panel())
        layout["footer"].update(self.get_activity_log_panel())

        return layout

    def update_layout(self):
        """Update all panels in the layout"""
        if self.layout:
            self.layout["left"].update(self.get_dates_status_panel())
            self.layout["session_info"].update(self.get_round_info_panel())
            self.layout["summary"].update(self.get_summary_panel())
            self.layout["current_op"].update(self.get_current_operation_panel())
            self.layout["footer"].update(self.get_activity_log_panel())

    def update_stats(self, completed: int = None, already_booked: int = None,
                    skipped: int = None, failed: int = None, total: int = None):
        """Update statistics"""
        if completed is not None:
            self.stats["completed"] = completed
        if already_booked is not None:
            self.stats["already_booked"] = already_booked
        if skipped is not None:
            self.stats["skipped"] = skipped
        if failed is not None:
            self.stats["failed"] = failed
        if total is not None:
            self.stats["total"] = total

    def set_operation(self, operation: str, step: str = ""):
        """Set the current operation text"""
        self.current_operation = operation
        self.current_step = step

        # Log to activity log if operation is set
        if operation:
            timestamp = datetime.now().strftime("%H:%M:%S")
            if step:
                self.log_activity(f"[{timestamp}] {operation} - {step}")
            else:
                self.log_activity(f"[{timestamp}] {operation}")

        if self.live_dashboard:
            self.update_layout()

    def log_activity(self, message: str):
        """Add a message to the activity log"""
        self.activity_log.append(message)
        # Keep only last N messages
        if len(self.activity_log) > self.max_activity_log:
            self.activity_log = self.activity_log[-self.max_activity_log:]
        if self.live_dashboard:
            self.update_layout()

    def start_countdown(self, seconds: int, message: str = ""):
        """Start a countdown timer"""
        self.countdown_seconds = seconds
        self.countdown_message = message
        if self.live_dashboard:
            self.update_layout()

    def update_countdown(self):
        """Decrement countdown by 1 second"""
        if self.countdown_seconds > 0:
            self.countdown_seconds -= 1
            if self.live_dashboard:
                self.update_layout()
        return self.countdown_seconds

    def stop_countdown(self):
        """Stop the countdown timer"""
        self.countdown_seconds = 0
        self.countdown_message = ""
        if self.live_dashboard:
            self.update_layout()

    def set_date_status(self, date: str, status: DateStatus, desk: str = None, attempt: int = None):
        """Update the status of a specific date"""
        self.date_statuses[date] = status
        if desk:
            self.date_desks[date] = desk
        if attempt is not None:
            self.date_attempts[date] = attempt
        if self.live_dashboard:
            self.update_layout()

    def initialize_dates(self, dates: List[str], existing_bookings: List[str] = None):
        """Initialize all dates with pending status"""
        for date in dates:
            if existing_bookings and date in existing_bookings:
                self.date_statuses[date] = DateStatus.ALREADY_BOOKED
            else:
                self.date_statuses[date] = DateStatus.PENDING
            self.date_attempts[date] = 0

        self.stats["total"] = len(dates)
        self.stats["already_booked"] = len(existing_bookings) if existing_bookings else 0

        if self.live_dashboard:
            self.update_layout()

    def start_live_dashboard(self):
        """Start the live dashboard"""
        self.layout = self.create_layout()
        self.live_dashboard = Live(
            self.layout,
            console=self.console,
            refresh_per_second=1,  # 1 FPS - perfect for countdown, minimal flickering
            screen=False,
            transient=False
        )
        self.live_dashboard.start()
        return self.live_dashboard

    def stop_live_dashboard(self):
        """Stop the live dashboard"""
        if self.live_dashboard:
            self.live_dashboard.stop()
            self.live_dashboard = None

    def add_date_attempt(self, date: str, success: bool = None):
        """Add a date to the attempted list"""
        if date not in self.dates_tried:
            self.dates_tried.append(date)

        if success is True and date not in self.successful_bookings:
            self.successful_bookings.append(date)
        elif success is False and date not in self.failed_dates:
            self.failed_dates.append(date)

    def print_header(self):
        """Print a beautiful header"""
        self.console.print()
        self.console.print(Panel(
            Align.center(Text("SpaceIQ Multi-Date Booking Bot", style="bold cyan")),
            style="bold white on blue",
            box=box.DOUBLE
        ))
        self.console.print()

    def print_mode_banner(self, mode: str):
        """Print mode banner"""
        mode_styles = {
            "headless": (">> HEADLESS MODE", "blue", "Background • Continuous • Auto-check"),
            "loop": (">> CONTINUOUS LOOP", "magenta", "Keeps trying forever • Ctrl+C to stop"),
            "poll": (">> POLLING MODE", "cyan", "Tries until success")
        }

        if mode in mode_styles:
            title, color, desc = mode_styles[mode]
            self.console.print(Panel(
                f"[bold {color}]{title}[/bold {color}]\n[dim]{desc}[/dim]",
                border_style=color,
                box=box.ROUNDED
            ))
            self.console.print()

    def print_date_header(self, date: str, idx: int, total: int):
        """Print a date header"""
        self.console.print(f"\n[bold magenta]=== [{idx}/{total}] {date} ===[/bold magenta]")

    def print_success(self, text: str):
        """Print success message"""
        self.console.print(f"[green][+][/green] {text}")

    def print_error(self, text: str):
        """Print error message"""
        self.console.print(f"[red][!][/red] {text}")

    def print_warning(self, text: str):
        """Print warning message"""
        self.console.print(f"[yellow][*][/yellow] {text}")

    def print_info(self, text: str):
        """Print info message"""
        self.console.print(f"[cyan][i][/cyan] {text}")

    def print_waiting(self, seconds: int, reason: str = "No seats available"):
        """Print waiting message with countdown"""
        self.console.print(f"\n[yellow][-] {reason}[/yellow]")
        self.console.print(f"[dim]Next check in {seconds}s ({seconds//60}m {seconds%60}s)[/dim]\n")

    def print_round_header(self, round_num: int, dates_count: int, existing_count: int = 0):
        """Print round header"""
        self.current_round = round_num

        info = f"Trying {dates_count} date(s)"
        if existing_count > 0:
            info += f" • {existing_count} already booked"

        self.console.print()
        self.console.print(Panel(
            f"[bold magenta]ROUND {round_num}[/bold magenta]\n[dim]{info}[/dim]",
            border_style="magenta",
            box=box.DOUBLE
        ))
        self.console.print()

    def print_summary_table(self, results: Dict[str, bool], existing_bookings: List[str] = None):
        """Print final summary table"""
        booked = [date for date, success in results.items() if success]
        skipped = [date for date, success in results.items() if not success]

        # Create summary table
        table = Table(title="== Booking Summary ==", box=box.ROUNDED, border_style="cyan")
        table.add_column("Status", style="bold", width=20)
        table.add_column("Count", justify="right", style="bold")
        table.add_column("Dates", style="dim")

        if existing_bookings:
            dates_str = ", ".join(sorted(existing_bookings)[:3])
            if len(existing_bookings) > 3:
                dates_str += f" +{len(existing_bookings)-3} more"
            table.add_row(
                "[cyan]Already Booked[/cyan]",
                f"[cyan]{len(existing_bookings)}[/cyan]",
                dates_str
            )

        if booked:
            dates_str = ", ".join(sorted(booked))
            table.add_row(
                "[green][+] Newly Booked[/green]",
                f"[green]{len(booked)}[/green]",
                dates_str
            )
        else:
            table.add_row(
                "[yellow]Newly Booked[/yellow]",
                "[yellow]0[/yellow]",
                "[dim]none[/dim]"
            )

        if skipped:
            dates_str = ", ".join(sorted(skipped)[:3])
            if len(skipped) > 3:
                dates_str += f" +{len(skipped)-3} more"
            table.add_row(
                "[yellow][-] Skipped[/yellow]",
                f"[yellow]{len(skipped)}[/yellow]",
                dates_str
            )

        self.console.print()
        self.console.print(table)
        self.console.print()

    def create_progress(self) -> Progress:
        """Create a progress bar for operations"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console
        )


# Global instance for easy access
ui = RichUI()
