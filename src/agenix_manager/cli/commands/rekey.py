from __future__ import annotations

import click

from ...ops.errors import AgenixOpError
from ...ops.rekey import rekey_secrets
from ..base import SecretCommand


@click.command()
@click.option("--all", "rekey_all", is_flag=True, help="Rekey all secrets")
@click.argument("names", nargs=-1, required=False)
@click.pass_context
def rekey(ctx: click.Context, names: tuple[str, ...], rekey_all: bool) -> None:
    """Re-encrypt one or more secrets with the current key set.

    Re-encrypts each listed secret so that only the current key-group
    members (as defined in the NixOS module) can decrypt it.

    Use --all to rekey every secret in the manifest.
    """
    RekeyCommand(ctx).run(names=list(names), rekey_all=rekey_all)


class RekeyCommand(SecretCommand):
    def run(self, names: list[str], rekey_all: bool = False, **kwargs: object) -> None:
        if rekey_all:
            secrets = self.cfg.secrets
            if not secrets:
                click.echo("[agenix-manager] No secrets to rekey.")
                return
        elif names:
            secrets = []
            for name in names:
                try:
                    secrets.append(self.resolve_secret(name))
                except KeyError as e:
                    click.echo(f"[agenix-manager] Error: {e}", err=True)
                    raise click.Abort from e
        else:
            click.echo(
                "[agenix-manager] Provide secret names or use --all to rekey everything.",
                err=True,
            )
            raise click.Abort

        try:
            rekey_secrets(self.cfg, secrets)
        except AgenixOpError as e:
            click.echo(f"[agenix-manager] Rekey failed: {e}", err=True)
            raise click.Abort from e

        for s in secrets:
            click.echo(f"[agenix-manager] Rekeyed '{s.name}.age'")
