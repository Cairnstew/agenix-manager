from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header

from ...config import NixConfig
from ...manifest import (
    ManifestError,
    find_manifest_path,
    load_manifest,
    remove_secret,
    save_manifest,
)
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

        if age_path.exists():
            age_path.unlink()
            self.notify(f"Deleted {name}.age", severity="information")
        else:
            self.notify(
                f"No .age file for '{name}', removing from manifest only",
                severity="warning",
            )

        manifest_path = find_manifest_path(self.cfg.secrets_path)
        if manifest_path.exists():
            try:
                manifest = load_manifest(manifest_path)
                manifest = remove_secret(manifest, name)
                save_manifest(manifest_path, manifest)
            except ManifestError as e:
                self.notify(str(e), severity="error")
                return

        table.refresh_data()
