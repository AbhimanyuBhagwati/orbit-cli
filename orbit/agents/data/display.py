from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from orbit.agents.data.intelligence import _format_size
from orbit.schemas.data import DataCatalog, TableProfile


def show_table_profile(console: Console, profile: TableProfile) -> None:
    """Display a rich table profile in the terminal."""
    # Header
    size = _format_size(profile.size_bytes)
    header = (
        f"[bold]Rows:[/] {profile.row_count:,}  |  "
        f"[bold]Columns:[/] {profile.column_count}  |  "
        f"[bold]Size:[/] {size}  |  "
        f"[bold]Quality:[/] {profile.quality_score}/100"
    )
    console.print(Panel(header, title=f"DATA PROFILE: {profile.table_name}", border_style="cyan"))

    # Column summary table
    col_table = Table(title="Column Summary", show_lines=False, pad_edge=False)
    col_table.add_column("Column", style="cyan", min_width=15)
    col_table.add_column("Type", style="dim")
    col_table.add_column("Nulls", justify="right")
    col_table.add_column("Unique", justify="right")
    col_table.add_column("Min", max_width=20)
    col_table.add_column("Max", max_width=20)
    col_table.add_column("Mean", justify="right")

    for col in profile.columns:
        null_style = "red" if col.null_pct > 20 else "yellow" if col.null_pct > 5 else ""
        null_str = f"[{null_style}]{col.null_pct}%[/]" if null_style else f"{col.null_pct}%"

        unique_str = f"{col.unique_count:,}"
        if col.unique_pct > 99:
            unique_str += " (unique)"

        mean_str = str(col.mean_value) if col.mean_value is not None else ""

        col_table.add_row(
            col.name,
            col.dtype,
            null_str,
            unique_str,
            (col.min_value or "")[:20],
            (col.max_value or "")[:20],
            mean_str,
        )

    console.print(col_table)

    # PII detections
    if profile.pii_detections:
        console.print()
        pii_table = Table(title="PII Detected", border_style="red")
        pii_table.add_column("Column", style="red bold")
        pii_table.add_column("Type")
        pii_table.add_column("Confidence")
        pii_table.add_column("Recommendation")

        for pii in profile.pii_detections:
            conf_style = "red" if pii.confidence == "high" else "yellow" if pii.confidence == "medium" else "dim"
            pii_table.add_row(
                pii.column_name,
                pii.pii_type,
                f"[{conf_style}]{pii.confidence}[/]",
                pii.recommendation,
            )
        console.print(pii_table)

    # Issues
    if profile.issues:
        console.print()
        console.print("[bold]Issues Found[/]")
        for issue in profile.issues:
            icon = {"critical": "[red]!!![/]", "warning": "[yellow]!![/]", "info": "[dim]i[/]"}.get(
                issue.severity, "[dim]?[/]"
            )
            col_str = f" ({issue.column})" if issue.column else ""
            console.print(f"  {icon} {issue.description}{col_str}")
            if issue.suggestion:
                console.print(f"      [dim]{issue.suggestion}[/]")

    # Suggestions summary
    console.print()
    critical_count = sum(1 for i in profile.issues if i.severity == "critical")
    warning_count = sum(1 for i in profile.issues if i.severity == "warning")
    if critical_count:
        console.print(f"[red bold]{critical_count} critical issues need attention[/]")
    if warning_count:
        console.print(f"[yellow]{warning_count} warnings to review[/]")
    if not critical_count and not warning_count:
        console.print("[green]No major issues found[/]")


def show_catalog(console: Console, catalog: DataCatalog) -> None:
    """Display the data catalog."""
    console.print(
        Panel(
            f"[bold]Tables:[/] {catalog.total_tables}  |  [bold]Total Columns:[/] {catalog.total_columns}",
            title="DATA CATALOG",
            border_style="cyan",
        )
    )

    cat_table = Table(show_lines=False)
    cat_table.add_column("Connection", style="cyan")
    cat_table.add_column("Table", style="bold")
    cat_table.add_column("Columns", justify="right")
    cat_table.add_column("Rows", justify="right")
    cat_table.add_column("Size", justify="right")

    for entry in catalog.entries:
        rows_str = f"{entry.row_count:,}" if entry.row_count is not None else "?"
        size_str = _format_size(entry.size_bytes)
        cat_table.add_row(
            entry.connection_name,
            entry.table_name,
            str(entry.column_count),
            rows_str,
            size_str,
        )

    console.print(cat_table)
