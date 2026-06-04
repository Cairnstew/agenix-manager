from __future__ import annotations

from textual.app import ComposeResult

from ..base import ReadOnlyScreen
from ..navigation import ScreenEntry, ScreenRegistry
from ..widgets.key_panel import KeyPanel
from ..widgets.secret_table import SecretTable


class StatusScreen(ReadOnlyScreen):
    def _compose_body(self) -> ComposeResult:
        yield KeyPanel(cfg=self.cfg)
        yield SecretTable(cfg=self.cfg)


ScreenRegistry.register(
    ScreenEntry(
        id="status",
        label="Status",
        description="View secret status",
        screen_cls=StatusScreen,
    )
)
