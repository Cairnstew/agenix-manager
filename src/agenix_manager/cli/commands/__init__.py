from .sync import sync
from .status import status
from .new import new
from .remove import remove
from .prune import prune
from .import_secrets import import_secrets
from .decrypt import decrypt
from .encrypt import encrypt
from .rekey import rekey


def register_commands(group: object) -> None:
    """Attach all subcommands to the main click Group."""
    group.add_command(sync)
    group.add_command(status)
    group.add_command(new)
    group.add_command(remove)
    group.add_command(prune)
    group.add_command(import_secrets)
    group.add_command(decrypt)
    group.add_command(encrypt)
    group.add_command(rekey)


__all__ = ["register_commands"]
