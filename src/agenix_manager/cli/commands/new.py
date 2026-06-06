from __future__ import annotations

import sys
from pathlib import Path

import click

from ...manifest import add_secret, remove_secret, update_secret
from ...ops.encrypt import encrypt_secret, encrypt_secret_from_stdin
from ...ops.errors import AgenixOpError
from ..base import ManifestWriteCommand


@click.command()
@click.option("--name", default=None, help="Secret name")
@click.option("--scope", default=None, help="Key scope (e.g. users, systems, all)")
@click.option("--owner", default="root", help="File owner")
@click.option("--group", default="root", help="File group")
@click.option("--mode", default="0400", help="File mode (octal)")
@click.option(
    "--stdin", is_flag=True, help="Read secret value from stdin instead of editor"
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing secret (delete and recreate)",
)
@click.option(
    "--update",
    is_flag=True,
    help="Update existing secret metadata without re-encrypting (or create if new)",
)
@click.pass_context
def new(
    ctx: click.Context,
    name: str | None,
    scope: str | None,
    owner: str,
    group: str,
    mode: str,
    stdin: bool,
    overwrite: bool,
    update: bool,
) -> None:
    """Create a new secret."""
    NewCommand(ctx).run(
        name=name, scope=scope, owner=owner, group=group, mode=mode,
        stdin=stdin, overwrite=overwrite, update=update,
    )


class NewCommand(ManifestWriteCommand):
    def run(
        self,
        name: str | None = None,
        scope: str | None = None,
        owner: str = "root",
        group: str = "root",
        mode: str = "0400",
        stdin: bool = False,
        overwrite: bool = False,
        update: bool = False,
        **kwargs: object,
    ) -> None:
        if name is not None and scope is not None:
            self._noninteractive(name, scope, owner, group, mode, stdin, overwrite, update)
            return
        if sys.stdin.isatty():
            self._tui()
        else:
            click.echo(
                "[agenix-manager] Piped input detected but --name and --scope are required.\n"
                "Usage: echo 'mysecret' | agenix-manager new --name mysecret --scope users",
                err=True,
            )
            raise click.Abort

    def _noninteractive(
        self,
        name: str,
        scope: str,
        owner: str,
        group: str,
        mode: str,
        stdin: bool,
        overwrite: bool,
        update: bool,
    ) -> None:
        if overwrite and update:
            click.echo(
                "[agenix-manager] Error: --overwrite and --update are mutually exclusive",
                err=True,
            )
            raise click.Abort

        available_scopes = ["all", "systems", "users", "other"]
        extra = (
            (self.cfg.keys.model_extra or {})
            if hasattr(self.cfg.keys, "model_extra")
            else {}
        )
        available_scopes.extend(extra.keys())
        if scope not in available_scopes:
            click.echo(
                f"[agenix-manager] Error: Unknown key scope '{scope}'. "
                f"Available scopes: {', '.join(available_scopes)}",
                err=True,
            )
            raise click.Abort

        exists = any(s.name == name for s in self.manifest.secrets)
        verb = "created"

        if exists:
            if overwrite:
                verb = "overwritten"
                age_file = Path(self.cfg.secrets_path) / f"{name}.age"
                if age_file.exists():
                    age_file.unlink()
                self.manifest = remove_secret(self.manifest, name)
                self.manifest = add_secret(
                    self.manifest, name=name, scope=scope, owner=owner, group=group, mode=mode
                )
            elif update:
                verb = "updated"
                self.manifest = update_secret(
                    self.manifest, name=name, scope=scope, owner=owner, group=group, mode=mode
                )
                if not stdin:
                    self._save_and_sync()
                    click.echo(f"[agenix-manager] Secret '{name}' {verb}.")
                    return
            else:
                click.echo(
                    f"[agenix-manager] Error: Secret '{name}' already exists in manifest. "
                    f"Use --overwrite or --update to modify it.",
                    err=True,
                )
                raise click.Abort
        else:
            self.manifest = add_secret(
                self.manifest, name=name, scope=scope, owner=owner, group=group, mode=mode
            )

        self._save_and_sync()

        secret = next(s for s in self.cfg.secrets if s.name == name)

        if stdin:
            plaintext = sys.stdin.read()
            encrypt_secret_from_stdin(self.cfg, secret, plaintext)
        else:
            encrypt_secret(self.cfg, secret)

        click.echo(f"[agenix-manager] Secret '{name}' {verb}.")
        click.echo(f"[agenix-manager]   Manifest: {self.manifest_path}")
        click.echo(f"[agenix-manager]   .age file: {secret.file}")
        click.echo(
            f"[agenix-manager]   Reference: config.age.secrets.{name}.path"
        )
        click.echo(
            f"[agenix-manager] Remember to run: git add {self.manifest_path} {self.cfg.secrets_path}/{name}.age"
        )

    def _tui(self) -> None:
        from ...tui.app import AgenixManagerApp
        from ...tui.screens.new_secret import NewSecretScreen

        app = AgenixManagerApp(
            cfg=self.cfg,
            initial_screen=NewSecretScreen,
            initial_screen_kwargs={"manifest_path": self.manifest_path},
        )
        app.run()
