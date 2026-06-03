from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from .config import NixConfig, SecretDef, load_from_cache, load_from_file, load_from_nix_eval
from .manifest import (
    Manifest,
    ManifestError,
    add_secret,
    find_manifest_path,
    load_manifest,
    remove_secret,
    resolve_all,
    save_manifest,
)
from .ops.encrypt import encrypt_secret, encrypt_secret_from_stdin
from .ops.errors import AgenixOpError
from .ops.remove import find_orphaned_secrets
from .secrets_nix import write_secrets_nix
from .state import compute_state


def _resolve_store_path(store_path: str) -> str | None:
    p = Path(store_path)
    parts = p.parts
    if len(parts) < 5 or parts[1] != "nix" or parts[2] != "store":
        return None

    relative = Path(*parts[4:])
    candidates = []

    if "PWD" in os.environ:
        candidates.append(Path(os.environ["PWD"]) / relative)
    candidates.append(Path.cwd() / relative)

    for candidate in candidates:
        if candidate.exists() and not str(candidate).startswith("/nix/store/"):
            return str(candidate)
    return None


def _resolve_secrets_path(cfg: NixConfig) -> NixConfig:
    resolved = _resolve_store_path(cfg.secrets_path)
    if resolved is None:
        return cfg

    click.echo(
        f"[agenix-manager] secretsPath resolved to Nix store path; using {resolved}",
        err=True,
    )
    new_secrets = [
        SecretDef(
            name=s.name,
            keys=s.keys,
            scope=s.scope,
            owner=s.owner,
            group=s.group,
            mode=s.mode,
            file=s.file.replace(cfg.secrets_path, resolved, 1),
        )
        for s in cfg.secrets
    ]
    return cfg.model_copy(update={"secrets_path": resolved, "secrets": new_secrets})


def _populate_from_manifest(cfg: NixConfig) -> tuple[NixConfig, Manifest | None]:
    manifest_path = find_manifest_path(cfg.secrets_path)
    if not manifest_path.exists():
        return cfg, None
    try:
        manifest = load_manifest(manifest_path)
        resolved = resolve_all(manifest, cfg.keys, cfg.secrets_path)
        if resolved:
            cfg = cfg.model_copy(update={"secrets": resolved})
        return cfg, manifest
    except ManifestError:
        return cfg, None


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
    if config_file:
        cfg = load_from_file(config_file)
    else:
        cache = load_from_cache(host)
        if cache is not None:
            cfg = cache
        else:
            try:
                cfg = load_from_nix_eval(host, flake_ref=flake)
            except AgenixOpError as e:
                msg = f"[agenix-manager] Error: {e.stderr.strip()}"
                if "flake" in e.stderr.lower() or "not found" in e.stderr.lower():
                    msg += "\n\nHint: Run from your flake directory, or use --flake /path/to/config"
                click.echo(msg, err=True)
                raise click.Abort from e

    cfg = _resolve_secrets_path(cfg)

    if extra_identities:
        cfg = cfg.model_copy(update={"identities": cfg.identities + list(extra_identities)})

    cfg, _manifest = _populate_from_manifest(cfg)

    try:
        written = write_secrets_nix(cfg)
    except OSError as e:
        click.echo(f"[agenix-manager] Error writing secrets.nix: {e}", err=True)
        raise click.Abort from e
    click.echo(f"[agenix-manager] secrets.nix synced -> {written}")

    ctx.ensure_object(dict)
    ctx.obj["cfg"] = cfg
    if _manifest is not None:
        ctx.obj["manifest"] = _manifest

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
            s.definition.scope,
            exists,
            f"{s.definition.owner}:{s.definition.mode}",
        )
    Console().print(table)


@main.command()
@click.argument("name")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def remove(ctx: click.Context, name: str, force: bool) -> None:
    """Delete a secret's .age file and remove from manifest."""
    cfg = ctx.obj["cfg"]
    manifest_path = find_manifest_path(cfg.secrets_path)
    age_file = Path(cfg.secrets_path) / f"{name}.age"

    if age_file.exists():
        if not force:
            click.confirm(f"Delete {age_file}?", abort=True)
        age_file.unlink()
        click.echo(f"[agenix-manager] Deleted {age_file}")
    else:
        click.echo(f"[agenix-manager] No .age file found for '{name}'")

    if manifest_path.exists():
        manifest = load_manifest(manifest_path)
        manifest = remove_secret(manifest, name)
        save_manifest(manifest_path, manifest)
        click.echo(f"[agenix-manager] Removed '{name}' from manifest")


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


@main.command()
@click.option("--name", default=None, help="Secret name")
@click.option("--scope", default=None, help="Key scope (e.g. users, systems, all)")
@click.option("--owner", default="root", help="File owner")
@click.option("--group", default="root", help="File group")
@click.option("--mode", default="0400", help="File mode (octal)")
@click.option("--stdin", is_flag=True, help="Read secret value from stdin instead of editor")
@click.pass_context
def new(
    ctx: click.Context,
    name: str | None,
    scope: str | None,
    owner: str,
    group: str,
    mode: str,
    stdin: bool,
) -> None:
    """Create a new secret."""
    cfg = ctx.obj["cfg"]
    manifest_path = find_manifest_path(cfg.secrets_path)

    if name is not None and scope is not None:
        _new_noninteractive(ctx, cfg, manifest_path, name, scope, owner, group, mode, stdin)
        return

    if sys.stdin.isatty():
        _new_tui(ctx, cfg, manifest_path)
    else:
        click.echo(
            "[agenix-manager] Piped input detected but --name and --scope are required.\n"
            "Usage: echo 'mysecret' | agenix-manager new --name mysecret --scope users",
            err=True,
        )
        raise click.Abort


def _new_noninteractive(
    ctx: click.Context,
    cfg: NixConfig,
    manifest_path: Path,
    name: str,
    scope: str,
    owner: str,
    group: str,
    mode: str,
    stdin: bool,
) -> None:
    from .manifest import Manifest

    try:
        manifest = load_manifest(manifest_path)
    except ManifestError:
        manifest = Manifest(version=1, secrets=[])

    if any(s.name == name for s in manifest.secrets):
        click.echo(f"[agenix-manager] Error: Secret '{name}' already exists in manifest", err=True)
        raise click.Abort

    available_scopes = ["all", "systems", "users", "other"]
    extra = (cfg.keys.model_extra or {}) if hasattr(cfg.keys, "model_extra") else {}
    available_scopes.extend(extra.keys())
    if scope not in available_scopes:
        click.echo(
            f"[agenix-manager] Error: Unknown key scope '{scope}'. "
            f"Available scopes: {', '.join(available_scopes)}",
            err=True,
        )
        raise click.Abort

    manifest = add_secret(manifest, name=name, scope=scope, owner=owner, group=group, mode=mode)
    save_manifest(manifest_path, manifest)

    resolved = resolve_all(manifest, cfg.keys, cfg.secrets_path)
    updated_cfg = cfg.model_copy(update={"secrets": resolved})
    write_secrets_nix(updated_cfg)

    secret = next(s for s in resolved if s.name == name)

    if stdin:
        plaintext = sys.stdin.read()
        encrypt_secret_from_stdin(cfg, secret, plaintext)
    else:
        encrypt_secret(updated_cfg, secret)

    click.echo(f"[agenix-manager] Secret '{name}' created.")
    click.echo(f"[agenix-manager]   Manifest: {manifest_path}")
    click.echo(f"[agenix-manager]   .age file: {secret.file}")
    click.echo(f"[agenix-manager]   Reference: config.age.secrets.{name}.path")
    click.echo(
        f"[agenix-manager] Remember to run: git add {manifest_path} {cfg.secrets_path}/{name}.age"
    )


def _new_tui(ctx: click.Context, cfg: NixConfig, manifest_path: Path) -> None:
    from .tui.app import AgenixManagerApp
    from .tui.screens.new_secret import NewSecretScreen

    app = AgenixManagerApp(
        cfg=cfg,
        initial_screen=NewSecretScreen,
        initial_screen_kwargs={"manifest_path": manifest_path},
    )
    app.run()
