"""
display.py
Rich terminal output for Cutman data.
"""

import sys
from datetime import datetime, timezone
from rich.console import Console
from rich.table import Table
from rich import box
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns
from rich.rule import Rule

# Write through whatever stdout main.py has configured (UTF-8 on Windows)
console = Console(file=sys.stdout, highlight=False, width=120)

PROMO_COLORS = {
    "UFC":      "bold red",
    "BOXING":   "bold blue",
    "PFL":      "bold green",
    "ONE":      "bold yellow",
    "BELLATOR": "bold magenta",
}


def _promo_style(promo: str) -> str:
    return PROMO_COLORS.get(promo.upper(), "bold white")


def print_fight_cards(events: list[dict], errors: dict) -> None:
    console.print()
    console.print(Rule("[bold red]UPCOMING FIGHT CARDS[/bold red]", style="red"))
    console.print()

    if not events:
        console.print("[dim]No events found.[/dim]")
    else:
        table = Table(
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style="bold white",
            border_style="dim",
            pad_edge=False,
            expand=False,
        )
        table.add_column("DATE",        style="dim",        min_width=14, no_wrap=True)
        table.add_column("PROMO",       min_width=8,        no_wrap=True)
        table.add_column("EVENT",       min_width=20)
        table.add_column("MAIN EVENT",  min_width=28)
        table.add_column("NETWORK",     style="dim",        min_width=12)

        for ev in events:
            promo = ev.get("promotion", "").upper()
            table.add_row(
                ev.get("date", "TBD"),
                Text(promo, style=_promo_style(promo)),
                ev.get("name", ""),
                ev.get("main_event", "") or ev.get("notes", ""),
                ev.get("network", ""),
            )

        console.print(table)

    # Source status
    _print_source_status(errors, label="Fight card sources")


def print_news(articles: list[dict], errors: dict) -> None:
    console.print()
    console.print(Rule("[bold red]LATEST MMA NEWS[/bold red]", style="red"))
    console.print()

    if not articles:
        console.print("[dim]No articles found.[/dim]")
    else:
        for i, art in enumerate(articles):
            pub: datetime = art["published"]
            if pub != datetime.min.replace(tzinfo=timezone.utc):
                age = datetime.now(timezone.utc) - pub
                hours = int(age.total_seconds() / 3600)
                age_str = f"{hours}h ago" if hours < 24 else f"{age.days}d ago"
            else:
                age_str = ""

            source_text = Text(f"[{art['source']}]", style="dim")
            age_text    = Text(f" {age_str}", style="dim italic")
            headline    = Text(art["title"], style="bold" if i < 5 else "")

            console.print(source_text + age_text)
            console.print(headline)
            if art.get("summary"):
                console.print(Text(art["summary"], style="dim"), end="\n")
            console.print()

    _print_source_status(errors, label="News sources")


def _print_source_status(errors: dict, label: str) -> None:
    if not errors:
        return
    ok    = [s for s, e in errors.items() if not e]
    fails = [(s, e) for s, e in errors.items() if e]

    status_parts = []
    if ok:
        status_parts.append(Text(f"OK  {', '.join(ok)}", style="dim green"))
    for src, err in fails:
        status_parts.append(Text(f"ERR {src}: {err}", style="dim red"))

    console.print(Text(f"{label}: ", style="dim") + Text(" | ").join(status_parts))
    console.print()
