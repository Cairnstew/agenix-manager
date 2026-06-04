from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding

from ...ops.errors import AgenixOpError
from ...ops.rekey import rekey_secrets
from ..base import TableScreen
from ..navigation import ScreenEntry, ScreenRegistry
from .rekey_confirm import RekeyConfirmScreen


class RekeyScreen(TableScreen):
    BINDINGS = [
        Binding("r", "rekey_selected", "Rekey"),
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def action_rekey_selected(self) -> None:
        secret = self._get_selected_secret()
        if secret is None:
            return

        confirm_screen = RekeyConfirmScreen(cfg=self.cfg, secret=secret)
        self.app.push_screen(confirm_screen, self._on_rekey_confirmed)

    def _on_rekey_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed:
            return
        secret = self._pending_secret
        try:
            rekey_secrets(self.cfg, [secret])
        except AgenixOpError as e:
            self._notify_err(f"Rekey failed: {e.stderr}")
            return
        self._notify_ok(f"Rekeyed '{secret.name}.age'")

    def _get_selected_secret(self):
        secret = super()._get_selected_secret()
        if secret is not None:
            self._pending_secret = secret
        return secret


ScreenRegistry.register(
    ScreenEntry(
        id="rekey",
        label="Rekey",
        description="Re-encrypt secrets with current keys",
        screen_cls=RekeyScreen,
    )
)
