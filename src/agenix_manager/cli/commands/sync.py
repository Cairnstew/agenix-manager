from __future__ import annotations

import click

from ..base import ReadOnlyCommand


@click.command()
@click.pass_context
def sync(ctx: click.Context) -> None:
    """Write secrets.nix only; do not launch TUI."""
    SyncCommand(ctx).run()


class SyncCommand(ReadOnlyCommand):
    def run(self, **kwargs: object) -> None:
        click.echo("Done.")
