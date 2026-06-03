from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from agenix_manager.ops.decrypt import decrypt_secret
from agenix_manager.ops.rekey import rekey_secrets


class TestDecrypt:
    def test_decrypt_builds_correct_cmd(self, sample_config):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "plaintext"
            result = decrypt_secret(sample_config, sample_config.secrets[0])
            assert result == "plaintext"
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "age"
            assert call_args[1] == "-d"
            assert call_args[2] == "-i"
            assert call_args[3] == "/etc/ssh/ssh_host_ed25519_key"
            assert call_args[4] == sample_config.secrets[0].file

    def test_decrypt_with_custom_identity(self, sample_config):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "plaintext"
            result = decrypt_secret(
                sample_config, sample_config.secrets[0], identity_path="/custom/id"
            )
            assert result == "plaintext"
            call_args = mock_run.call_args[0][0]
            assert "-i" in call_args
            assert "/custom/id" in call_args


class TestRekey:
    def test_rekey_builds_correct_cmd(self, sample_config_with_tmp):
        secrets_dir = Path(sample_config_with_tmp.secrets_path)
        secrets_dir.mkdir(parents=True, exist_ok=True)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            rekey_secrets(sample_config_with_tmp, sample_config_with_tmp.secrets)
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "agenix"
            assert call_args[1] == "--rekey"
            assert "github-token.age" in call_args
            assert "db-password.age" in call_args

    def test_rekey_subset(self, sample_config_with_tmp):
        secrets_dir = Path(sample_config_with_tmp.secrets_path)
        secrets_dir.mkdir(parents=True, exist_ok=True)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = ""
            rekey_secrets(sample_config_with_tmp, [sample_config_with_tmp.secrets[0]])
            call_args = mock_run.call_args[0][0]
            assert "github-token.age" in call_args
            assert "db-password.age" not in call_args
