from typing import Any

from textual.widgets import Static

from ...config import NixConfig


class KeyPanel(Static):
    def __init__(self, cfg: NixConfig, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cfg = cfg

    def render(self) -> str:
        k = self.cfg.keys
        return (
            f"[bold]Key groups[/bold]\n"
            f"  systems : {len(k.systems)}\n"
            f"  users   : {len(k.users)}\n"
            f"  other   : {len(k.other)}\n"
            f"  all     : {len(k.all)}\n"
        )
