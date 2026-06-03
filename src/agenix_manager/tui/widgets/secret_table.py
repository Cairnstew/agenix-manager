from textual.widgets import DataTable

from ...config import NixConfig
from ...state import compute_state


class SecretTable(DataTable):
    def __init__(self, cfg: NixConfig, show_missing_only: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.cfg = cfg
        self.show_missing_only = show_missing_only

    def on_mount(self) -> None:
        self.add_columns("Secret", "Scope", "Status", "Owner", "Mode")
        self.refresh_data()

    def refresh_data(self) -> None:
        self.clear()
        statuses = compute_state(self.cfg)
        for s in statuses:
            if self.show_missing_only and s.age_file_exists:
                continue
            status_str = "Y" if s.age_file_exists else "N"
            self.add_row(
                s.definition.name,
                s.definition.keys,
                status_str,
                s.definition.owner,
                s.definition.mode,
                key=s.definition.name,
            )
