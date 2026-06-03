from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header

from ...config import NixConfig
from ...ops.errors import AgenixOpError
from ...ops.rekey import rekey_secrets
from ..widgets.secret_table import SecretTable
from .rekey_confirm import RekeyConfirmScreen


class RekeyScreen(Screen[None]):
    BINDINGS = [
        Binding("r", "rekey_selected", "Rekey"),
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, cfg: NixConfig, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cfg = cfg

    def compose(self) -> ComposeResult:
        yield Header()
        self.table = SecretTable(cfg=self.cfg)
        yield self.table
        yield Footer()

    def action_rekey_selected(self) -> None:
        row_index = self.table.cursor_row
        if row_index is None:
            self.notify("No secret selected", severity="warning")
            return
        row = self.table.get_row_at(row_index)
        if row is None:
            return
        name = str(row[0])
        secret = next((s for s in self.cfg.secrets if s.name == name), None)
        if secret is None:
            self.notify(f"Secret '{name}' not found in config", severity="error")
            return

        self._pending_secret = secret
        confirm_screen = RekeyConfirmScreen(cfg=self.cfg, secret=secret)
        self.app.push_screen(confirm_screen, self._on_rekey_confirmed)

    def _on_rekey_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed:
            return
        secret = self._pending_secret
        try:
            rekey_secrets(self.cfg, [secret])
        except AgenixOpError as e:
            self.notify(f"Rekey failed: {e.stderr}", severity="error")
            return

        self.notify(f"Rekeyed '{secret.name}.age'", severity="information")
