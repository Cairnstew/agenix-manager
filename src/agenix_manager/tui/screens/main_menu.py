from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, ListItem, ListView, Static

from ...config import NixConfig
from ..navigation import ScreenRegistry


class MainMenuScreen(Screen[None]):
    def __init__(self, cfg: NixConfig, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cfg = cfg

    def compose(self) -> ComposeResult:
        yield Header()
        items = [
            ListItem(
                Static(f"{entry.label} - {entry.description}"),
                id=entry.id,
            )
            for entry in ScreenRegistry.get_all()
        ]
        yield ListView(*items)
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id
        if item_id is None:
            return
        entry = ScreenRegistry.get(item_id)
        if entry is None:
            return
        kwargs: dict[str, Any] = {}
        if entry.kwargs_factory:
            kwargs = entry.kwargs_factory(self.cfg)
        screen = entry.screen_cls(cfg=self.cfg, **kwargs)
        self.app.push_screen(screen)
