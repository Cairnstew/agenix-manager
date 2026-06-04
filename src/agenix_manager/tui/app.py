from typing import Any

from textual.app import App

from ..config import NixConfig
from .screens.status import StatusScreen


class AgenixManagerApp(App[None]):
    TITLE = "agenix-manager"
    CSS_PATH = None
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, cfg: NixConfig, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cfg = cfg

    def on_mount(self) -> None:
        self.push_screen(StatusScreen(cfg=self.cfg))
