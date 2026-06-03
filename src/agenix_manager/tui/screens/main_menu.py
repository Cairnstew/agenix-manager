from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, ListItem, ListView, Static

from ...config import NixConfig
from .decrypt import DecryptScreen
from .encrypt import EncryptScreen
from .rekey import RekeyScreen
from .status import StatusScreen


class MainMenuScreen(Screen):
    def __init__(self, cfg: NixConfig, **kwargs):
        super().__init__(**kwargs)
        self.cfg = cfg

    def compose(self) -> ComposeResult:
        yield Header()
        yield ListView(
            ListItem(Static("Status - View secret status"), id="status"),
            ListItem(Static("Encrypt - Edit/create a secret"), id="encrypt"),
            ListItem(Static("Decrypt - View a secret"), id="decrypt"),
            ListItem(Static("Rekey - Re-encrypt secrets"), id="rekey"),
        )
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        screens = {
            "status": StatusScreen,
            "encrypt": EncryptScreen,
            "decrypt": DecryptScreen,
            "rekey": RekeyScreen,
        }
        screen_cls = screens.get(item_id)
        if screen_cls:
            self.app.push_screen(screen_cls(cfg=self.cfg))
