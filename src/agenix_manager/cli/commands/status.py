from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from ...state import compute_state
from ..base import ReadOnlyCommand


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Print secret status table to stdout."""
    StatusCommand(ctx).run()


class StatusCommand(ReadOnlyCommand):
    def run(self, **kwargs: object) -> None:
        statuses = compute_state(self.cfg)
        table = Table(title="agenix-manager status")
        table.add_column("Secret", style="cyan")
        table.add_column("Keys scope")
        table.add_column(".age exists")
        table.add_column("Owner/Mode")
        for s in statuses:
            exists = "[green]Y[/]" if s.age_file_exists else "[red]N[/]"
            table.add_row(
                s.definition.name,
                s.definition.scope,
                exists,
                f"{s.definition.owner}:{s.definition.mode}",
            )
        Console().print(table)
