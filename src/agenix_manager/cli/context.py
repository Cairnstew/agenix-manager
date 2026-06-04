from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import click

from ..config import (
    NixConfig,
    SecretDef,
    load_from_cache,
    load_from_file,
    load_from_nix_eval,
)
from ..manifest import Manifest, ManifestError, find_manifest_path, resolve_all
from ..ops.errors import AgenixOpError
from ..secrets_nix import write_secrets_nix


@dataclass
class AppContext:
    """Typed context shared across all CLI commands."""

    cfg: NixConfig
    manifest: Manifest | None = None


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


def bootstrap(
    host: str | None,
    flake: str,
    config_file: Path | None,
    extra_identities: tuple[str, ...],
) -> AppContext:
    """Load config, resolve paths, populate from manifest, write secrets.nix.

    Returns an AppContext ready to be stored in click's ctx.obj.
    """
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
        cfg = cfg.model_copy(
            update={"identities": cfg.identities + list(extra_identities)}
        )
    cfg, manifest = _populate_from_manifest(cfg)
    try:
        written = write_secrets_nix(cfg)
    except OSError as e:
        click.echo(f"[agenix-manager] Error writing secrets.nix: {e}", err=True)
        raise click.Abort from e
    click.echo(f"[agenix-manager] secrets.nix synced -> {written}")
    return AppContext(cfg=cfg, manifest=manifest)
