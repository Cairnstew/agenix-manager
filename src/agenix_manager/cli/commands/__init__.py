from .sync import sync
from .status import status
from .new import new
from .remove import remove
from .prune import prune


def register_commands(group: object) -> None:
    """Attach all subcommands to the main click Group."""
    group.add_command(sync)
    group.add_command(status)
    group.add_command(new)
    group.add_command(remove)
    group.add_command(prune)


__all__ = ["register_commands"]
