from rich.console import Console
from rich.table import Table

console = Console()


def print_status_table(rows: list[tuple[str, bool, str]]) -> None:
    table = Table(title="CLI Authentication Status")
    table.add_column("Tool", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Details")

    for tool, ok, details in rows:
        status = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
        table.add_row(tool, status, details)

    console.print(table)


def success(msg: str) -> None:
    console.print(f"[green]>[/green] {msg}")


def warning(msg: str) -> None:
    console.print(f"[yellow]>[/yellow] {msg}")


def error(msg: str) -> None:
    console.print(f"[red]>[/red] {msg}")


def info(msg: str) -> None:
    console.print(f"[blue]>[/blue] {msg}")
