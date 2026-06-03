from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Label

from ...config import NixConfig
from ...ops.encrypt import encrypt_secret
from ...ops.errors import AgenixOpError
from ..widgets.secret_table import SecretTable


class EncryptScreen(Screen[None]):
    BINDINGS = [
        Binding("e", "encrypt_selected", "Encrypt"),
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, cfg: NixConfig, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cfg = cfg

    def compose(self) -> ComposeResult:
        yield Header()
        self.table = SecretTable(cfg=self.cfg, show_present_only=True)
        yield self.table
        yield Label(
            "Create new secrets via [bold]New secret[/] in the main menu",
            id="encrypt-hint",
        )
        yield Footer()

    def on_mount(self) -> None:
        hint = self.query_one("#encrypt-hint", Label)
        hint.styles.padding = (0, 2)
        hint.styles.text_align = "center"
        hint.styles.color = "gray"

    async def action_encrypt_selected(self) -> None:
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
            async with self.app.suspend():
                encrypt_secret(self.cfg, secret)
            self.table.refresh_data()
            self.notify(f"Edited existing secret '{name}.age'", severity="information")
        except AgenixOpError as e:
            self.notify(f"Encrypt failed: {e.stderr}", severity="error")
            self.table.refresh_data()
