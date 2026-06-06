from __future__ import annotations

import click

from ...ops.encrypt import encrypt_secret
from ...ops.errors import AgenixOpError
from ..base import SecretCommand


@click.command()
@click.argument("name")
@click.pass_context
def encrypt(ctx: click.Context, name: str) -> None:
    """Edit/re-encrypt an existing secret via ``$EDITOR``.

    Launches the editor configured in the ``$EDITOR`` (or ``$VISUAL``)
    environment variable.  After the editor exits the secret is
    re-encrypted with the current key set.
    """
    EncryptCommand(ctx).run(name=name)


class EncryptCommand(SecretCommand):
    def run(self, name: str, **kwargs: object) -> None:
        try:
            secret = self.resolve_secret(name)
        except KeyError as e:
            click.echo(f"[agenix-manager] Error: {e}", err=True)
            raise click.Abort from e

        try:
            encrypt_secret(self.cfg, secret)
        except AgenixOpError as e:
            click.echo(f"[agenix-manager] Encryption failed: {e}", err=True)
            raise click.Abort from e

        click.echo(f"[agenix-manager] Secret '{name}.age' re-encrypted.")
