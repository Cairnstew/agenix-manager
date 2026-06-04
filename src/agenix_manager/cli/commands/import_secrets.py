from __future__ import annotations

import click

from ...manifest import ManifestError, add_secret
from ...ops.discover import find_untracked_secrets
from ..base import ManifestWriteCommand


@click.command()
@click.option("--scope", default="all", help="Key scope for imported secrets")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def import_secrets(ctx: click.Context, scope: str, force: bool) -> None:
    """Add untracked .age files to the manifest."""
    ImportCommand(ctx).run(scope=scope, force=force)


class ImportCommand(ManifestWriteCommand):
    def run(self, scope: str = "all", force: bool = False, **kwargs: object) -> None:
        untracked = find_untracked_secrets(self.cfg)
        if not untracked:
            click.echo("[agenix-manager] No untracked .age files found")
            return
        click.echo(
            f"[agenix-manager] Found {len(untracked)} untracked .age file(s):"
        )
        for f in untracked:
            click.echo(f"  {f.name}")
        if not force:
            click.confirm(
                f"Add to manifest with scope '{scope}'?", abort=True
            )
        for f in untracked:
            try:
                self.manifest = add_secret(
                    self.manifest, name=f.stem, scope=scope
                )
            except ManifestError as e:
                click.echo(f"[agenix-manager] Skipping {f.name}: {e}")
        self._save_and_sync()
        count = len(untracked)
        click.echo(f"[agenix-manager] Imported {count} secret(s)")
