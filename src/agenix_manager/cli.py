from __future__ import annotations

from pathlib import Path

import click

from .config import load_from_file, load_from_nix_eval
from .secrets_nix import write_secrets_nix
from .state import compute_state


@click.group(invoke_without_command=True)
@click.option("--host", default=None, help="NixOS hostname to eval config for")
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
def main(ctx: click.Context, host, config_file, extra_identities):
    """agenix-manager: declarative agenix TUI."""
    if config_file:
        cfg = load_from_file(config_file)
    else:
        cfg = load_from_nix_eval(host)

    if extra_identities:
        cfg.identities = list(cfg.identities) + list(extra_identities)

    written = write_secrets_nix(cfg)
    click.echo(f"[agenix-manager] secrets.nix synced -> {written}")

    ctx.ensure_object(dict)
    ctx.obj["cfg"] = cfg

    if ctx.invoked_subcommand is None:
        from .tui.app import AgenixManagerApp

        app = AgenixManagerApp(cfg=cfg)
        app.run()


@main.command()
@click.pass_context
def sync(ctx):
    """Write secrets.nix only; do not launch TUI."""
    click.echo("Done.")


@main.command()
@click.pass_context
def status(ctx):
    """Print secret status table to stdout."""
    from rich.console import Console
    from rich.table import Table

    cfg = ctx.obj["cfg"]
    statuses = compute_state(cfg)
    table = Table(title="agenix-manager status")
    table.add_column("Secret", style="cyan")
    table.add_column("Keys scope")
    table.add_column(".age exists")
    table.add_column("Owner/Mode")
    for s in statuses:
        exists = "[green]Y[/]" if s.age_file_exists else "[red]N[/]"
        table.add_row(
            s.definition.name,
            s.definition.keys,
            exists,
            f"{s.definition.owner}:{s.definition.mode}",
        )
    Console().print(table)
