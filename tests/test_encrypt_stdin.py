from __future__ import annotations

from unittest.mock import patch

import pytest

from agenix_manager.config import NixConfig, SecretDef
from agenix_manager.ops.encrypt import encrypt_secret_from_stdin
from agenix_manager.ops.errors import AgenixOpError


class TestEncryptFromStdin:
    def test_encrypt_stdin_builds_correct_cmd(self):
        cfg = NixConfig(
            secretsPath="/secrets",
            identities=[],
            keys={"systems": [], "users": [], "other": [], "all": []},
            secrets=[],
        )
        secret = SecretDef(
            name="test",
            keys=["ssh-ed25519 AAAA...key1", "ssh-ed25519 AAAA...key2"],
            file="/secrets/test.age",
        )
        with patch("subprocess.run") as mock_run:
            encrypt_secret_from_stdin(cfg, secret, "myplaintext")
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "age"
            assert call_args[1] == "-e"
            assert call_args[2] == "-a"
            assert call_args[3] == "-r"
            assert call_args[4] == "ssh-ed25519 AAAA...key1"
            assert call_args[5] == "-r"
            assert call_args[6] == "ssh-ed25519 AAAA...key2"
            assert call_args[7] == "-o"
            assert call_args[8] == "/secrets/test.age"

    def test_encrypt_stdin_passes_plaintext(self):
        cfg = NixConfig(
            secretsPath="/secrets",
            identities=[],
            keys={"systems": [], "users": [], "other": [], "all": []},
            secrets=[],
        )
        secret = SecretDef(
            name="test",
            keys=["ssh-ed25519 AAAA...key1"],
            file="/secrets/test.age",
        )
        with patch("subprocess.run") as mock_run:
            encrypt_secret_from_stdin(cfg, secret, "myplaintext")
            assert mock_run.call_args[1]["input"] == "myplaintext"
            assert mock_run.call_args[1]["text"] is True

    def test_encrypt_stdin_raises_on_failure(self):
        cfg = NixConfig(
            secretsPath="/secrets",
            identities=[],
            keys={"systems": [], "users": [], "other": [], "all": []},
            secrets=[],
        )
        secret = SecretDef(
            name="test",
            keys=["ssh-ed25519 AAAA...key1"],
            file="/secrets/test.age",
        )
        with patch("subprocess.run") as mock_run:
            import subprocess

            mock_run.side_effect = subprocess.CalledProcessError(
                1, ["age", "-e", "-a", "-r", "key", "-o", "out"], stderr="error"
            )
            with pytest.raises(AgenixOpError):
                encrypt_secret_from_stdin(cfg, secret, "plaintext")

    def test_encrypt_stdin_single_key(self):
        cfg = NixConfig(
            secretsPath="/secrets",
            identities=[],
            keys={"systems": [], "users": [], "other": [], "all": []},
            secrets=[],
        )
        secret = SecretDef(
            name="single",
            keys=["ssh-ed25519 AAAA...onlykey"],
            file="/secrets/single.age",
        )
        with patch("subprocess.run") as mock_run:
            encrypt_secret_from_stdin(cfg, secret, "data")
            cmd = mock_run.call_args[0][0]
            assert cmd.count("-r") == 1
            assert cmd[cmd.index("-r") + 1] == "ssh-ed25519 AAAA...onlykey"
