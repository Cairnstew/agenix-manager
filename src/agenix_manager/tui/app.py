from typing import Any

from textual.app import App

from ..config import NixConfig
from . import screens
from .screens.main_menu import MainMenuScreen


class AgenixManagerApp(App[None]):
    TITLE = "agenix-manager"
    CSS_PATH = None
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(
        self,
        cfg: NixConfig,
        initial_screen: type[Any] | None = None,
        initial_screen_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.cfg = cfg
        self._initial_screen = initial_screen
        self._initial_screen_kwargs = initial_screen_kwargs or {}

    def on_mount(self) -> None:
        if self._initial_screen:
            screen = self._initial_screen(cfg=self.cfg, **self._initial_screen_kwargs)
            self.push_screen(screen)
        else:
            self.push_screen(MainMenuScreen(cfg=self.cfg))
