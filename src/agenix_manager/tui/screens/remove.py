from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding

from ...manifest import remove_secret, save_manifest
from ..base import MutateTableScreen
from ..navigation import ScreenEntry, ScreenRegistry


class RemoveScreen(MutateTableScreen):
    BINDINGS = [
        Binding("d", "delete_selected", "Delete selected"),
        Binding("escape", "app.pop_screen", "Back"),
    ]

    async def action_delete_selected(self) -> None:
        row_index = self.table.cursor_row
        if row_index is None:
            self.notify("No secret selected", severity="warning")
            return
        row = self.table.get_row_at(row_index)
        if row is None:
            return
        name = str(row[0])

        age_path = Path(self.cfg.secrets_path) / f"{name}.age"
        if age_path.exists():
            age_path.unlink()
            self._notify_ok(f"Deleted {name}.age")
        else:
            self.notify(
                f"No .age file for '{name}', removing from manifest only",
                severity="warning",
            )

        if self.manifest_path.exists():
            self.manifest = remove_secret(self.manifest, name)
            save_manifest(self.manifest_path, self.manifest)

        self._sync()
        self._refresh_table()


ScreenRegistry.register(
    ScreenEntry(
        id="remove",
        label="Remove",
        description="Delete a secret's .age file",
        screen_cls=RemoveScreen,
    )
)
