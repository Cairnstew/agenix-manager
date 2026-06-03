from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header

from ...config import NixConfig
from ..widgets.secret_table import SecretTable


class RemoveScreen(Screen[None]):
    BINDINGS = [
        Binding("d", "delete_selected", "Delete selected"),
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, cfg: NixConfig, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cfg = cfg

    def compose(self) -> ComposeResult:
        yield Header()
        table = SecretTable(cfg=self.cfg)
        table.cursor_type = "row"
        yield table
        yield Footer()

    def action_delete_selected(self) -> None:
        table = self.query_one(SecretTable)
        row_index = table.cursor_row
        if row_index is None:
            self.notify("No secret selected", severity="warning")
            return
        row = table.get_row_at(row_index)
        if row is None:
            return
        name = str(row[0])
        age_path = Path(self.cfg.secrets_path) / f"{name}.age"
        if not age_path.exists():
            self.notify(f"No .age file found for '{name}'", severity="error")
            return
        age_path.unlink()
        table.refresh_data()
        self.notify(f"Deleted {name}.age", severity="information")
