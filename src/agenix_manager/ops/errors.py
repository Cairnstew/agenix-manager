from __future__ import annotations


class AgenixOpError(Exception):
    def __init__(self, command: str, stderr: str, returncode: int) -> None:
        self.command = command
        self.stderr = stderr
        self.returncode = returncode
        super().__init__(f"{command} failed (exit {returncode}): {stderr}")
