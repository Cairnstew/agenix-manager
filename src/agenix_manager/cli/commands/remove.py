from __future__ import annotations

import socket
from pathlib import Path

import click

from ...manifest import remove_secret, resolve_all, save_manifest
from ...secrets_nix import write_secrets_nix
from ..base import SecretCommand


@click.command()
@click.argument("name")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def remove(ctx: click.Context, name: str, force: bool) -> None:
    """Delete a secret's .age file and remove from manifest."""
    RemoveCommand(ctx).run(name=name, force=force)


class RemoveCommand(SecretCommand):
    def run(self, name: str, force: bool = False, **kwargs: object) -> None:
        age_file = Path(self.cfg.secrets_path) / f"{name}.age"
        if age_file.exists():
            if not force:
                click.confirm(f"Delete {age_file}?", abort=True)
            age_file.unlink()
            click.echo(f"[agenix-manager] Deleted {age_file}")
        else:
            click.echo(f"[agenix-manager] No .age file found for '{name}'")

        if self.manifest_path.exists():
            self.manifest = remove_secret(self.manifest, name)
            save_manifest(self.manifest_path, self.manifest)
            click.echo(f"[agenix-manager] Removed '{name}' from manifest")

        resolved = resolve_all(self.manifest, self.cfg.keys, self.cfg.secrets_path, socket.gethostname())
        self.cfg = self.cfg.model_copy(update={"secrets": resolved})
        write_secrets_nix(self.cfg)
        self.app_ctx.cfg = self.cfg


