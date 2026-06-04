from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Label

from ...ops.encrypt import encrypt_secret
from ...ops.errors import AgenixOpError
from ..base import TableScreen
from ..navigation import ScreenEntry, ScreenRegistry
from ..widgets.secret_table import SecretTable


class EncryptScreen(TableScreen):
    BINDINGS = [
        Binding("e", "encrypt_selected", "Encrypt"),
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def _create_table(self) -> SecretTable:
        return SecretTable(cfg=self.cfg, show_present_only=True)

    def _compose_body(self) -> ComposeResult:
        yield from super()._compose_body()
        yield Label(
            "Create new secrets via [bold]New secret[/] in the main menu",
            id="encrypt-hint",
        )

    def on_mount(self) -> None:
        hint = self.query_one("#encrypt-hint", Label)
        hint.styles.padding = (0, 2)
        hint.styles.text_align = "center"
        hint.styles.color = "gray"

    async def action_encrypt_selected(self) -> None:
        secret = self._get_selected_secret()
        if secret is None:
            return
        try:
            with self.app.suspend():
                encrypt_secret(self.cfg, secret)
            self._refresh_table()
            self._notify_ok(f"Edited existing secret '{secret.name}.age'")
        except AgenixOpError as e:
            self._notify_err(f"Encrypt failed: {e.stderr}")
            self._refresh_table()


ScreenRegistry.register(
    ScreenEntry(
        id="encrypt",
        label="Encrypt",
        description="Edit / re-encrypt a secret",
        screen_cls=EncryptScreen,
    )
)
