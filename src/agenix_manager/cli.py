from __future__ import annotations

from pathlib import Path

import click

from .config import load_from_file, load_from_nix_eval
from .ops.remove import find_orphaned_secrets
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
def main(
    ctx: click.Context,
    host: str | None,
    config_file: Path | None,
    extra_identities: tuple[str, ...],
) -> None:
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
def sync(ctx: click.Context) -> None:
    """Write secrets.nix only; do not launch TUI."""
    click.echo("Done.")


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
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


@main.command()
@click.argument("name")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def remove(ctx: click.Context, name: str, force: bool) -> None:
    """Delete a secret's .age file."""
    cfg = ctx.obj["cfg"]
    age_file = Path(cfg.secrets_path) / f"{name}.age"
    if not age_file.exists():
        click.echo(f"[agenix-manager] No .age file found for '{name}'")
        return
    if not force:
        click.confirm(f"Delete {age_file}?", abort=True)
    age_file.unlink()
    click.echo(f"[agenix-manager] Deleted {age_file}")


@main.command()
@click.option("--force", is_flag=True, help="Skip all confirmation prompts")
@click.pass_context
def prune(ctx: click.Context, force: bool) -> None:
    """Delete .age files not referenced in config."""
    cfg = ctx.obj["cfg"]
    orphans = find_orphaned_secrets(cfg)
    if not orphans:
        click.echo("[agenix-manager] No orphaned .age files found")
        return
    click.echo(f"[agenix-manager] Found {len(orphans)} orphaned .age file(s):")
    for f in orphans:
        click.echo(f"  {f.name}")
    if not force:
        click.confirm("Delete all orphaned files?", abort=True)
    for f in orphans:
        f.unlink()
        click.echo(f"[agenix-manager] Deleted {f}")
