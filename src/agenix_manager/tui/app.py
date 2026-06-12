from typing import Any

from textual.app import App
from textual.screen import Screen

from ..config import NixConfig
from .screens.status import StatusScreen


class AgenixManagerApp(App[None]):
    TITLE = "agenix-manager"
    CSS_PATH = None
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(
        self,
        cfg: NixConfig,
        initial_screen: type[Screen[Any]] | None = None,
        initial_screen_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.cfg = cfg
        self._initial_screen = initial_screen
        self._initial_screen_kwargs = initial_screen_kwargs or {}

    def on_mount(self) -> None:
        if self._initial_screen is not None:
            self.push_screen(self._initial_screen(cfg=self.cfg, **self._initial_screen_kwargs))
        else:
            self.push_screen(StatusScreen(cfg=self.cfg))
