from typing import Any

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, ListItem, ListView, Static

from ...config import NixConfig
from ...manifest import find_manifest_path
from .decrypt import DecryptScreen
from .encrypt import EncryptScreen
from .new_secret import NewSecretScreen
from .rekey import RekeyScreen
from .remove import RemoveScreen
from .status import StatusScreen


class MainMenuScreen(Screen[None]):
    def __init__(self, cfg: NixConfig, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cfg = cfg

    def compose(self) -> ComposeResult:
        yield Header()
        yield ListView(
            ListItem(Static("Status - View secret status"), id="status"),
            ListItem(Static("New secret - Create a new secret"), id="new-secret"),
            ListItem(Static("Encrypt - Edit/re-encrypt a secret"), id="encrypt"),
            ListItem(Static("Decrypt - View a secret"), id="decrypt"),
            ListItem(Static("Rekey - Re-encrypt secrets"), id="rekey"),
            ListItem(Static("Remove - Delete a secret's .age file"), id="remove"),
        )
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        if item_id is None:
            return
        if item_id == "new-secret":
            manifest_path = find_manifest_path(self.cfg.secrets_path)
            screen: Screen[Any] = NewSecretScreen(cfg=self.cfg, manifest_path=manifest_path)
            self.app.push_screen(screen)
            return
        screens: dict[str, type[Screen[Any]]] = {
            "status": StatusScreen,
            "encrypt": EncryptScreen,
            "decrypt": DecryptScreen,
            "rekey": RekeyScreen,
            "remove": RemoveScreen,
        }
        screen_cls = screens.get(item_id)
        if screen_cls:
            screen = screen_cls(cfg=self.cfg)  # type: ignore[call-arg]
            self.app.push_screen(screen)
