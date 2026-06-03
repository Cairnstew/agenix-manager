from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header

from ...config import NixConfig
from ...ops.decrypt import decrypt_secret
from ...ops.errors import AgenixOpError
from ..widgets.secret_table import SecretTable
from .decrypt_view import DecryptViewScreen


class DecryptScreen(Screen[None]):
    BINDINGS = [
        Binding("d", "decrypt_selected", "Decrypt"),
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, cfg: NixConfig, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cfg = cfg

    def compose(self) -> ComposeResult:
        yield Header()
        self.table = SecretTable(cfg=self.cfg, show_missing_only=False)
        yield self.table
        yield Footer()

    def action_decrypt_selected(self) -> None:
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

        try:
            plaintext = decrypt_secret(self.cfg, secret)
        except AgenixOpError as e:
            self.notify(f"Decrypt failed: {e.stderr}", severity="error")
            return

        self.app.push_screen(DecryptViewScreen(plaintext=plaintext, secret_name=name))
