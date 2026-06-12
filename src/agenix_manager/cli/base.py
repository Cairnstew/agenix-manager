from __future__ import annotations

import socket
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import click

from ..config import NixConfig, SecretDef
from ..manifest import (
    Manifest,
    ManifestError,
    find_manifest_path,
    load_manifest,
    resolve_all,
    save_manifest,
)
from ..secrets_nix import write_secrets_nix
from .context import AppContext


def load_manifest_or_empty(path: Path) -> Manifest:
    try:
        return load_manifest(path)
    except ManifestError:
        return Manifest(version=1, secrets=[])


class BaseCommand(ABC):
    """Root of the command class hierarchy.

    Every CLI command inherits from this. Provides direct access to the
    resolved config, manifest, and manifest path via ``self``.
    """

    def __init__(self, ctx: click.Context) -> None:
        self.ctx = ctx
        self.app_ctx: AppContext = ctx.obj
        self.cfg: NixConfig = self.app_ctx.cfg
        self.manifest: Manifest | None = self.app_ctx.manifest
        self.manifest_path: Path = find_manifest_path(self.cfg.secrets_path, self.cfg.manifest_path)

    @abstractmethod
    def run(self, **kwargs: Any) -> None:
        """Execute the command."""
        ...


class ReadOnlyCommand(BaseCommand):
    """Commands that read state but never modify the manifest or secrets."""

    @abstractmethod
    def run(self, **kwargs: Any) -> None:
        ...


class ManifestCommand(BaseCommand):
    """Commands that need the manifest. Auto-loads if not already present."""

    def __init__(self, ctx: click.Context) -> None:
        super().__init__(ctx)
        if self.manifest is None:
            self.manifest = load_manifest_or_empty(self.manifest_path)


class ManifestReadCommand(ManifestCommand):
    """Commands that read from the manifest without modifying it."""

    @abstractmethod
    def run(self, **kwargs: Any) -> None:
        ...


class ManifestWriteCommand(ManifestCommand):
    """Commands that modify the manifest. Provides ``_save_and_sync()``."""

    def _save_and_sync(self) -> None:
        """Persist the in-memory manifest to disk and re-sync secrets.nix.

        Call this after mutating ``self.manifest``.
        """
        save_manifest(self.manifest_path, self.manifest)
        resolved = resolve_all(self.manifest, self.cfg.keys, self.cfg.secrets_path, socket.gethostname())
        self.cfg = self.cfg.model_copy(update={"secrets": resolved})
        write_secrets_nix(self.cfg)
        self.app_ctx.cfg = self.cfg
        self.app_ctx.manifest = self.manifest
        self.ctx.obj = self.app_ctx

    @abstractmethod
    def run(self, **kwargs: Any) -> None:
        ...


class SecretCommand(ManifestWriteCommand):
    """Commands that operate on a specific named secret."""

    def resolve_secret(self, name: str) -> SecretDef:
        for s in self.cfg.secrets:
            if s.name == name:
                return s
        raise KeyError(f"Secret '{name}' not found in resolved config")

    @abstractmethod
    def run(self, **kwargs: Any) -> None:
        ...
