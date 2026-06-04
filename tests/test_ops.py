from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from agenix_manager.ops.decrypt import decrypt_secret
from agenix_manager.ops.rekey import rekey_secrets
from agenix_manager.ops.remove import find_orphaned_secrets, remove_secret_file


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

        with (
            patch("subprocess.run") as mock_run,
            patch(
                "agenix_manager.ops.base.BaseOp._find_agenix",
                return_value="/fake/bin/agenix",
            ),
        ):
            mock_run.return_value.stdout = ""
            rekey_secrets(sample_config_with_tmp, sample_config_with_tmp.secrets)
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "/fake/bin/agenix"
            assert call_args[1] == "--rekey"
            assert "github-token.age" in call_args
            assert "db-password.age" in call_args

    def test_rekey_subset(self, sample_config_with_tmp):
        secrets_dir = Path(sample_config_with_tmp.secrets_path)
        secrets_dir.mkdir(parents=True, exist_ok=True)

        with (
            patch("subprocess.run") as mock_run,
            patch(
                "agenix_manager.ops.base.BaseOp._find_agenix",
                return_value="/fake/bin/agenix",
            ),
        ):
            mock_run.return_value.stdout = ""
            rekey_secrets(sample_config_with_tmp, [sample_config_with_tmp.secrets[0]])
            call_args = mock_run.call_args[0][0]
            assert "/fake/bin/agenix" in call_args
            assert "--rekey" in call_args
            assert "github-token.age" in call_args
            assert "db-password.age" not in call_args


class TestRemove:
    def test_remove_existing_file(self, sample_config_with_tmp):
        secrets_dir = Path(sample_config_with_tmp.secrets_path)
        age_file = secrets_dir / "github-token.age"
        age_file.write_text("encrypted")
        result = remove_secret_file(sample_config_with_tmp, "github-token")
        assert result == age_file
        assert not age_file.exists()

    def test_remove_missing_file(self, sample_config_with_tmp):
        result = remove_secret_file(sample_config_with_tmp, "github-token")
        assert result is None

    def test_find_orphans_none(self, sample_config_with_tmp):
        secrets_dir = Path(sample_config_with_tmp.secrets_path)
        for secret in sample_config_with_tmp.secrets:
            file = secrets_dir / f"{secret.name}.age"
            file.write_text("encrypted")
        orphans = find_orphaned_secrets(sample_config_with_tmp)
        assert orphans == []

    def test_find_orphans_with_extra(self, sample_config_with_tmp):
        secrets_dir = Path(sample_config_with_tmp.secrets_path)
        (secrets_dir / "orphan.age").write_text("encrypted")
        (secrets_dir / "another.age").write_text("encrypted")
        orphans = find_orphaned_secrets(sample_config_with_tmp)
        assert len(orphans) == 2
        assert all(f.name in {"orphan.age", "another.age"} for f in orphans)
