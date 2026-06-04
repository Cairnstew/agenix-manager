from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding

from ...ops.decrypt import decrypt_secret
from ...ops.errors import AgenixOpError
from ..base import TableScreen
from ..navigation import ScreenEntry, ScreenRegistry
from .decrypt_view import DecryptViewScreen


class DecryptScreen(TableScreen):
    BINDINGS = [
        Binding("d", "decrypt_selected", "Decrypt"),
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def action_decrypt_selected(self) -> None:
        secret = self._get_selected_secret()
        if secret is None:
            return
        try:
            plaintext = decrypt_secret(self.cfg, secret)
        except AgenixOpError as e:
            self._notify_err(f"Decrypt failed: {e.stderr}")
            return
        self.app.push_screen(
            DecryptViewScreen(plaintext=plaintext, secret_name=secret.name)
        )


ScreenRegistry.register(
    ScreenEntry(
        id="decrypt",
        label="Decrypt",
        description="View a secret's plaintext",
        screen_cls=DecryptScreen,
    )
)
