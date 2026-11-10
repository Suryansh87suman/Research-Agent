"""
main.py — CLI entry point for the Research Agent.

Usage
-----
  python main.py --query "transformer models in drug discovery"
  python main.py --query "climate change AI" --sources arxiv semantic_scholar
  python main.py --query "CRISPR applications" --hypotheses 5
  python main.py --query "quantum computing" --max-papers 15 --output-file my_report.md
"""

import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

console = Console()


def _banner() -> None:
    console.print(
        Panel.fit(
            "[bold blue]IBM Research Agent[/bold blue]\n"
            "[dim]Powered by IBM Granite on IBM Cloud Lite[/dim]",
            border_style="blue",
        )
    )


@click.command()
@click.option(
    "--query", "-q",
    required=True,
    help="Research question or topic to investigate.",
)
@click.option(
    "--sources", "-s",
    multiple=True,
    default=["arxiv", "semantic_scholar", "crossref"],
    show_default=True,
    help="Data sources to search (repeatable). Options: arxiv, semantic_scholar, crossref.",
)
@click.option(
    "--hypotheses", "-H",
    default=3,
    show_default=True,
    type=click.IntRange(1, 5),
    help="Number of hypotheses to generate (1-5).",
)
@click.option(
    "--max-papers", "-m",
    default=10,
    show_default=True,
    type=click.IntRange(1, 50),
    help="Maximum papers to retrieve.",
)
@click.option(
    "--output-file", "-o",
    default=None,
    help="Filename for the output Markdown report (saved to outputs/).",
)
@click.option(
    "--no-report",
    is_flag=True,
    default=False,
    help="Skip full report generation (faster).",
)
@click.option(
    "--compare",
    is_flag=True,
    default=False,
    help="Generate a comparative analysis across retrieved papers.",
)
def main(query, sources, hypotheses, max_papers, output_file, no_report, compare):
    """IBM Research Agent — autonomous academic literature research powered by IBM Granite."""
    _banner()

    # Late import so config errors surface clearly
    try:
        from research_agent.agent import ResearchAgent
        from research_agent import config
        config.MAX_PAPERS_PER_QUERY = max_papers
    except EnvironmentError as exc:
        console.print(f"[bold red]Configuration Error:[/bold red] {exc}")
        console.print(
            "\n[yellow]Tip:[/yellow] Copy [bold]env.example[/bold] to [bold].env.local[/bold] "
            "and fill in your IBM Cloud credentials."
        )
        sys.exit(1)

    agent = ResearchAgent(verbose=False)

    # ── Search ──────────────────────────────────────────────────────────────
    console.rule("[bold]Step 1 — Literature Search[/bold]")
    with console.status("Searching academic databases …"):
        papers = agent.search(query, sources=list(sources))

    if not papers:
        console.print("[bold red]No papers found.[/bold red] Try a different query.")
        sys.exit(0)

    # Display results table
    table = Table(title=f"Found {len(papers)} Papers", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", max_width=55)
    table.add_column("Authors", max_width=25)
    table.add_column("Year", justify="right", width=6)
    table.add_column("Source", width=12)
    for i, p in enumerate(papers, 1):
        authors = ", ".join(p.authors[:2]) + (" et al." if len(p.authors) > 2 else "")
        table.add_row(str(i), p.title[:54], authors[:24], str(p.year or "-"), p.source)
    console.print(table)

    # ── Summaries ────────────────────────────────────────────────────────────
    console.rule("[bold]Step 2 — Paper Summaries[/bold]")
    for paper in papers[:5]:  # show first 5 summaries interactively
        with console.status(f"Summarising: {paper.title[:50]} …"):
            summary = agent.summarize_paper(paper)
        console.print(Panel(summary, title=f"[cyan]{paper.title[:60]}[/cyan]", expand=False))

    # ── Comparative analysis (optional) ──────────────────────────────────────
    if compare and len(papers) >= 2:
        console.rule("[bold]Comparative Analysis[/bold]")
        with console.status("Generating comparative analysis …"):
            comparison = agent.compare_papers(papers[:6])
        console.print(Panel(comparison, title="[magenta]Comparative Analysis[/magenta]", expand=False))

    # ── Hypotheses ───────────────────────────────────────────────────────────
    console.rule(f"[bold]Step 3 — Hypothesis Generation ({hypotheses})[/bold]")
    with console.status("Generating hypotheses via IBM Granite …"):
        hyps = agent.generate_hypotheses(query, papers, count=hypotheses)
    for i, h in enumerate(hyps, 1):
        console.print(f"  [bold green]H{i}.[/bold green] {h}")

    # ── Full report ───────────────────────────────────────────────────────────
    if not no_report:
        console.rule("[bold]Step 4 — Report Generation[/bold]")
        agent.add_citations(papers)
        with console.status("Writing report (this may take a moment) …"):
            report_path = agent.write_report(query, papers, filename=output_file)
            bibtex_path = agent.export_citations("bibtex")
            apa_path = agent.export_citations("apa")

        console.print(f"\n[bold green]✓[/bold green] Report   → [underline]{report_path}[/underline]")
        console.print(f"[bold green]✓[/bold green] BibTeX  → [underline]{bibtex_path}[/underline]")
        console.print(f"[bold green]✓[/bold green] APA Refs → [underline]{apa_path}[/underline]")

    console.rule()
    console.print("[bold blue]Research Agent complete.[/bold blue]")


if __name__ == "__main__":
    main()
