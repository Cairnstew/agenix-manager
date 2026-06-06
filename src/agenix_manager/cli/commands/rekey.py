from __future__ import annotations

import click

from ...ops.errors import AgenixOpError
from ...ops.rekey import rekey_secrets
from ..base import SecretCommand


@click.command()
@click.argument("names", nargs=-1, required=True)
@click.pass_context
def rekey(ctx: click.Context, names: tuple[str, ...]) -> None:
    """Re-encrypt one or more secrets with the current key set.

    Re-encrypts each listed secret so that only the current key-group
    members (as defined in the NixOS module) can decrypt it.
    """
    RekeyCommand(ctx).run(names=list(names))


class RekeyCommand(SecretCommand):
    def run(self, names: list[str], **kwargs: object) -> None:
        secrets = []
        for name in names:
            try:
                secrets.append(self.resolve_secret(name))
            except KeyError as e:
                click.echo(f"[agenix-manager] Error: {e}", err=True)
                raise click.Abort from e

        try:
            rekey_secrets(self.cfg, secrets)
        except AgenixOpError as e:
            click.echo(f"[agenix-manager] Rekey failed: {e}", err=True)
            raise click.Abort from e

        for name in names:
            click.echo(f"[agenix-manager] Rekeyed '{name}.age'")
