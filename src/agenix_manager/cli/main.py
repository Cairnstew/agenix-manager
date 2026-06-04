from __future__ import annotations

from pathlib import Path

import click

from .commands import register_commands
from .context import bootstrap


@click.group(invoke_without_command=True)
@click.option("--host", default=None, help="NixOS hostname to eval config for")
@click.option(
    "--flake",
    default=".",
    help="Flake reference for nix eval (default: .)",
    show_default=True,
)
@click.option(
    "--config-file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
)
@click.option(
    "-i",
    "--identity",
    "extra_identities",
    multiple=True,
    help="Extra identity file paths for decryption",
)
@click.pass_context
def main(
    ctx: click.Context,
    host: str | None,
    flake: str,
    config_file: Path | None,
    extra_identities: tuple[str, ...],
) -> None:
    """agenix-manager: declarative agenix TUI."""
    ctx.obj = bootstrap(host, flake, config_file, extra_identities)

    if ctx.invoked_subcommand is None:
        from ..tui.app import AgenixManagerApp

        app = AgenixManagerApp(cfg=ctx.obj.cfg)
        app.run()


register_commands(main)
