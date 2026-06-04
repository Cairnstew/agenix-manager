from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding

from ..actions import (
    DecryptAction,
    EncryptAction,
    NewSecretAction,
    RekeyAction,
    RemoveAction,
)
from ..base import TableScreen
from ..widgets.key_panel import KeyPanel
from ..widgets.secret_table import SecretTable


class StatusScreen(TableScreen):
    BINDINGS = [
        Binding("n", "new_secret", "New"),
        Binding("e", "encrypt", "Encrypt"),
        Binding("d", "decrypt", "Decrypt"),
        Binding("r", "rekey", "Rekey"),
        Binding("R", "remove", "Remove"),
    ]

    def __init__(self, cfg, **kwargs):
        super().__init__(cfg, **kwargs)
        self._new_secret_action = NewSecretAction(self)
        self._encrypt_action = EncryptAction(self)
        self._decrypt_action = DecryptAction(self)
        self._rekey_action = RekeyAction(self)
        self._remove_action = RemoveAction(self)

    def _compose_body(self) -> ComposeResult:
        yield KeyPanel(cfg=self.cfg)
        yield SecretTable(cfg=self.cfg)

    def action_new_secret(self) -> None:
        self._new_secret_action.execute()

    def action_encrypt(self) -> None:
        self._encrypt_action.execute()

    def action_decrypt(self) -> None:
        self._decrypt_action.execute()

    def action_rekey(self) -> None:
        self._rekey_action.execute()

    def action_remove(self) -> None:
        self._remove_action.execute()
