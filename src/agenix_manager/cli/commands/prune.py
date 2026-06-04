from __future__ import annotations

import click

from ...ops.remove import find_orphaned_secrets
from ..base import ReadOnlyCommand


@click.command()
@click.option("--force", is_flag=True, help="Skip all confirmation prompts")
@click.pass_context
def prune(ctx: click.Context, force: bool) -> None:
    """Delete .age files not referenced in config."""
    PruneCommand(ctx).run(force=force)


class PruneCommand(ReadOnlyCommand):
    def run(self, force: bool = False, **kwargs: object) -> None:
        orphans = find_orphaned_secrets(self.cfg)
        if not orphans:
            click.echo("[agenix-manager] No orphaned .age files found")
            return
        click.echo(f"[agenix-manager] Found {len(orphans)} orphaned .age file(s):")
        for f in orphans:
            click.echo(f"  {f.name}")
        if not force:
            click.confirm("Delete all orphaned files?", abort=True)
        for f in orphans:
            f.unlink()
            click.echo(f"[agenix-manager] Deleted {f}")
