from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from ..config import NixConfig
from .screens.main_menu import MainMenuScreen


class AgenixManagerApp(App):
    TITLE = "agenix-manager"
    CSS_PATH = None
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, cfg: NixConfig, **kwargs):
        super().__init__(**kwargs)
        self.cfg = cfg

    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen(cfg=self.cfg))
