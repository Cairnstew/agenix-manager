from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header

from ...config import NixConfig
from ..widgets.key_panel import KeyPanel
from ..widgets.secret_table import SecretTable


class StatusScreen(Screen):
    def __init__(self, cfg: NixConfig, **kwargs):
        super().__init__(**kwargs)
        self.cfg = cfg

    def compose(self) -> ComposeResult:
        yield Header()
        yield KeyPanel(cfg=self.cfg)
        yield SecretTable(cfg=self.cfg)
        yield Footer()
