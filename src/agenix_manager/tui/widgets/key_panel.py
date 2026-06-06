from typing import Any

from textual.widgets import Static

from ...config import NixConfig


class KeyPanel(Static):
    def __init__(self, cfg: NixConfig, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.cfg = cfg

    def render(self) -> str:
        k = self.cfg.keys
        extra = (k.model_extra or {}) if hasattr(k, "model_extra") else {}
        lines = ["[bold]Key groups[/bold]"]
        for name in sorted(extra):
            lines.append(f"  {name.ljust(10)}: {len(extra[name])}")
        return "\n".join(lines)
