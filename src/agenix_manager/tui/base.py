from __future__ import annotations

import socket
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen, Screen
from textual.widgets import Footer, Header

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
from .widgets.secret_table import SecretTable


class BaseScreen(Screen[None]):
    """Root of the TUI screen class hierarchy.

    Every screen inherits from this. Provides automatic Header + Footer
    composition, a standard escape binding, and helper methods.
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, cfg: NixConfig, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cfg = cfg

    def compose(self) -> ComposeResult:
        yield Header()
        yield from self._compose_body()
        yield Footer()

    def _compose_body(self) -> ComposeResult:
        raise NotImplementedError

    def _notify_ok(self, message: str) -> None:
        self.notify(message, severity="information")

    def _notify_warn(self, message: str) -> None:
        self.notify(message, severity="warning")

    def _notify_err(self, message: str) -> None:
        self.notify(message, severity="error")

    def _resolve_secret(self, name: str) -> SecretDef | None:
        for s in self.cfg.secrets:
            if s.name == name:
                return s
        self._notify_err(f"Secret '{name}' not found in config")
        return None


class ReadOnlyScreen(BaseScreen):
    """Marker base for screens that never mutate state."""

    def _compose_body(self) -> ComposeResult:
        raise NotImplementedError


class TableScreen(BaseScreen):
    """Screen centred around a SecretTable with selection helpers."""

    def __init__(self, cfg: NixConfig, **kwargs: Any) -> None:
        super().__init__(cfg, **kwargs)
        self._table: SecretTable | None = None

    def _create_table(self) -> SecretTable:
        return SecretTable(cfg=self.cfg)

    def _compose_body(self) -> ComposeResult:
        self._table = self._create_table()
        yield self._table

    @property
    def table(self) -> SecretTable:
        if self._table is None:
            self._table = self.query_one(SecretTable)
        return self._table

    def _get_selected_secret(self) -> SecretDef | None:
        row_index = self.table.cursor_row
        if row_index is None or not self.table.is_valid_row_index(row_index):
            self.notify("No secret selected", severity="warning")
            return None
        row = self.table.get_row_at(row_index)
        name = str(row[0])
        return self._resolve_secret(name)

    def _refresh_table(self) -> None:
        self.table.cfg = self.cfg
        self.table.refresh_data()


class MutateTableScreen(TableScreen):
    """Table screen that reads and writes the manifest file.

    Provides ``_sync()`` to persist manifest changes and regenerate
    ``secrets.nix``.
    """

    def __init__(self, cfg: NixConfig, **kwargs: Any) -> None:
        super().__init__(cfg, **kwargs)
        self.manifest_path: Path = find_manifest_path(self.cfg.secrets_path, self.cfg.manifest_path)
        try:
            self.manifest: Manifest = load_manifest(self.manifest_path)
        except ManifestError:
            self.manifest = Manifest(version=1, secrets=[])

    def _sync(self) -> None:
        resolved = resolve_all(self.manifest, self.cfg.keys, self.cfg.secrets_path, socket.gethostname())
        self.cfg = self.cfg.model_copy(update={"secrets": resolved})
        self.app.cfg = self.cfg
        write_secrets_nix(self.cfg)


class WizardScreen(BaseScreen):
    """Multi-step wizard framework.

    Manages step state, navigation bindings, and lifecycle hooks.
    Subclasses implement ``_render_step``, ``_validate_step``, and
    ``_on_finish``.
    """

    total_steps: int = 1

    BINDINGS = [
        Binding("escape", "go_back_or_exit", "Back"),
        Binding("enter", "advance_or_create", "Confirm"),
    ]

    def __init__(self, cfg: NixConfig, **kwargs: Any) -> None:
        super().__init__(cfg, **kwargs)
        self.step = 1

    def action_advance_or_create(self) -> None:
        if self.step >= self.total_steps:
            self._on_finish()
        else:
            if self._validate_step(self.step):
                self.step += 1
                self._render_step(self.step)

    def action_go_back_or_exit(self) -> None:
        if self.step <= 1:
            self.app.pop_screen()
        else:
            self.step -= 1
            self._render_step(self.step)

    def _validate_step(self, step: int) -> bool:
        return True

    def _render_step(self, step: int) -> None:
        raise NotImplementedError

    def _on_finish(self) -> None:
        pass


class ViewerModalScreen(ModalScreen[None]):
    """Display-only modal that closes on q or Escape."""

    BINDINGS = [
        Binding("q", "dismiss_modal", "Close"),
        Binding("escape", "dismiss_modal", "Close"),
    ]

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)


class ConfirmModalScreen(ModalScreen[bool]):
    """Yes / No confirmation modal.

    Press ``y`` to confirm, ``n`` or Escape to cancel.
    """

    BINDINGS = [
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
        Binding("enter", "confirm", "Yes"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)
