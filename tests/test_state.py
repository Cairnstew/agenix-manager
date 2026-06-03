from __future__ import annotations

from pathlib import Path

from agenix_manager.state import SecretStatus, compute_state, missing_secrets, present_secrets
from agenix_manager.config import SecretDef


class TestSecretState:
    def test_compute_state_all_missing(self, sample_config_with_tmp):
        statuses = compute_state(sample_config_with_tmp)
        assert len(statuses) == 2
        for s in statuses:
            assert not s.age_file_exists
            assert isinstance(s.age_file_path, Path)

    def test_compute_state_some_present(self, sample_config_with_tmp):
        (Path(sample_config_with_tmp.secrets_path) / "github-token.age").touch()
        statuses = compute_state(sample_config_with_tmp)
        status_by_name = {s.definition.name: s for s in statuses}

        assert status_by_name["github-token"].age_file_exists
        assert not status_by_name["db-password"].age_file_exists

    def test_missing_secrets(self, sample_config_with_tmp):
        (Path(sample_config_with_tmp.secrets_path) / "github-token.age").touch()
        missing = missing_secrets(sample_config_with_tmp)
        assert len(missing) == 1
        assert missing[0].name == "db-password"

    def test_present_secrets(self, sample_config_with_tmp):
        (Path(sample_config_with_tmp.secrets_path) / "github-token.age").touch()
        present = present_secrets(sample_config_with_tmp)
        assert len(present) == 1
        assert present[0].name == "github-token"

    def test_secret_status_dataclass(self, sample_config):
        definition = sample_config.secrets[0]
        status = SecretStatus(
            definition=definition,
            age_file_exists=True,
            age_file_path=Path("/tmp/test.age"),
        )
        assert status.definition == definition
        assert status.age_file_exists
        assert str(status.age_file_path) == "/tmp/test.age"
