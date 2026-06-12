from __future__ import annotations

import click

from ...manifest import ManifestError, add_secret
from ...ops.discover import find_untracked_secrets
from ..base import ManifestWriteCommand


@click.command()
@click.option("--scope", default="all", help="Key scope for imported secrets")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.option("--name", "-n", "names", multiple=True,
              help="Import only the named secret(s) (omit .age suffix). Repeatable.")
@click.pass_context
def import_secrets(ctx: click.Context, scope: str, force: bool, names: tuple[str, ...]) -> None:
    """Add untracked .age files to the manifest."""
    ImportCommand(ctx).run(scope=scope, force=force, names=names)


class ImportCommand(ManifestWriteCommand):
    def run(self, scope: str = "all", force: bool = False,
            names: tuple[str, ...] = (), **kwargs: object) -> None:
        untracked = find_untracked_secrets(self.cfg)
        if not untracked:
            click.echo("[agenix-manager] No untracked .age files found")
            return

        if names:
            selected = [f for f in untracked if f.stem in names]
            missing = set(names) - {f.stem for f in untracked}
            if missing:
                click.echo(
                    f"[agenix-manager] Skipping (not found): {', '.join(sorted(missing))}",
                    err=True,
                )
        else:
            selected = untracked

        if not selected:
            click.echo("[agenix-manager] No matching .age files to import")
            return

        click.echo(
            f"[agenix-manager] Found {len(selected)} untracked .age file(s):"
        )
        for f in selected:
            click.echo(f"  {f.name}")
        if not force:
            click.confirm(
                f"Add to manifest with scope '{scope}'?", abort=True
            )
        for f in selected:
            try:
                self.manifest = add_secret(
                    self.manifest, name=f.stem, scope=scope
                )
            except ManifestError as e:
                click.echo(f"[agenix-manager] Skipping {f.name}: {e}")
        self._save_and_sync()
        count = len(selected)
        click.echo(f"[agenix-manager] Imported {count} secret(s)")
