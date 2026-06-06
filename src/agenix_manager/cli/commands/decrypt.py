from __future__ import annotations

import click

from ...ops.decrypt import decrypt_secret
from ...ops.errors import AgenixOpError
from ..base import SecretCommand


@click.command()
@click.argument("name")
@click.option(
    "-i",
    "--identity",
    default=None,
    help="Override identity file for this decryption",
)
@click.pass_context
def decrypt(ctx: click.Context, name: str, identity: str | None) -> None:
    """Decrypt and print a secret's plaintext value to stdout."""
    DecryptCommand(ctx).run(name=name, identity=identity)


class DecryptCommand(SecretCommand):
    def run(self, name: str, identity: str | None = None, **kwargs: object) -> None:
        try:
            secret = self.resolve_secret(name)
        except KeyError as e:
            click.echo(f"[agenix-manager] Error: {e}", err=True)
            raise click.Abort from e

        try:
            plaintext = decrypt_secret(self.cfg, secret, identity_path=identity)
        except AgenixOpError as e:
            click.echo(f"[agenix-manager] Decryption failed: {e}", err=True)
            raise click.Abort from e

        click.echo(plaintext, nl=False)
