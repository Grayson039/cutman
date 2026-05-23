"""
main.py — Cutman Phase 1 data runner
Fetches upcoming fight cards + latest MMA news and prints to terminal.
"""

# ── Force UTF-8 on Windows consoles before importing Rich ──────────────────
import sys
import io

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Now import Rich (it will write through the UTF-8 wrapper) ───────────────
from scrapers.fight_cards import get_upcoming_events
from parsers.news_feed import fetch_news
from utils.display import print_fight_cards, print_news
from rich.console import Console
from rich.rule import Rule

console = Console(file=sys.stdout, highlight=False, width=120)


def main():
    console.print()
    console.print(
        "[bold red]CUTMAN[/bold red] [dim]// Phase 1 Data Layer[/dim]",
        justify="center",
    )
    console.print()

    # ── Fight cards ────────────────────────────────────────────
    console.print("[dim]Fetching fight cards...[/dim]")
    events, card_errors = get_upcoming_events()
    print_fight_cards(events, card_errors)

    # ── News ───────────────────────────────────────────────────
    console.print("[dim]Fetching news feeds...[/dim]")
    articles, news_errors = fetch_news()
    print_news(articles, news_errors)

    console.print(Rule(style="dim"))
    console.print(
        f"[dim]  {len(events)} events  |  {len(articles)} articles[/dim]",
        justify="center",
    )
    console.print()


if __name__ == "__main__":
    main()
