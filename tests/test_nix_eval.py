from __future__ import annotations

import json
import subprocess
from pathlib import Path

from agenix_manager.config import NixConfig

FIXTURES = Path(__file__).parent / "nix"


def nix_eval(
    nix_file: str,
    attr: str = "config.agenixManager.cliConfig",
) -> dict:
    result = subprocess.run(
        ["nix", "eval", "-f", str(FIXTURES / nix_file), attr, "--json", "--impure"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def nix_eval_error(nix_file: str, attr: str = "config") -> str:
    result = subprocess.run(
        ["nix", "eval", "-f", str(FIXTURES / nix_file), attr, "--json", "--impure"],
        capture_output=True,
        text=True,
    )
    return result.stderr


class TestNixEvalSimple:
    def test_cli_config_structure(self):
        data = nix_eval("eval-simple.nix")
        assert set(data.keys()) == {
            "secretsPath",
            "secretsNixPath",
            "flakeRoot",
            "identities",
            "keys",
            "secrets",
        }

    def test_parses_as_valid_nix_config(self):
        data = nix_eval("eval-simple.nix")
        cfg = NixConfig.model_validate(data)
        assert cfg.secrets_path == "/secrets"
        assert cfg.flake_root == "/etc/nixos"

    def test_single_secret(self):
        data = nix_eval("eval-simple.nix")
        assert len(data["secrets"]) == 1
        assert data["secrets"][0]["name"] == "t1"

    def test_key_scope_resolution_systems(self):
        data = nix_eval("eval-simple.nix")
        keys = data["keys"]
        assert len(keys["all"]) == 1
        assert keys["all"] == keys["systems"]
        assert keys["users"] == []
        assert keys["other"] == []

    def test_identities_passthrough(self):
        data = nix_eval("eval-simple.nix")
        assert data["identities"] == ["/etc/ssh/ssh_host_ed25519_key"]

    def test_secret_defaults(self):
        data = nix_eval("eval-simple.nix")
        secret = data["secrets"][0]
        assert secret["owner"] == "root"
        assert secret["group"] == "root"
        assert secret["mode"] == "0400"


class TestNixEvalFull:
    def test_four_secrets(self):
        data = nix_eval("eval-full.nix", "config.agenixManager.cliConfig")
        assert len(data["secrets"]) == 4

    def test_all_key_scopes(self):
        data = nix_eval("eval-full.nix", "config.agenixManager.cliConfig")
        keys = data["keys"]
        assert len(keys["systems"]) == 1
        assert len(keys["users"]) == 1
        assert len(keys["other"]) == 1
        assert len(keys["all"]) == 3

    def test_custom_owner_group_mode(self):
        data = nix_eval("eval-full.nix", "config.agenixManager.cliConfig")
        secrets = {s["name"]: s for s in data["secrets"]}
        assert secrets["sys-key"]["owner"] == "root"
        assert secrets["sys-key"]["group"] == "root"
        assert secrets["sys-key"]["mode"] == "0400"
        assert secrets["user-token"]["owner"] == "alice"
        assert secrets["user-token"]["group"] == "users"
        assert secrets["user-token"]["mode"] == "0600"
        assert secrets["global-db"]["owner"] == "postgres"
        assert secrets["global-db"]["group"] == "postgres"
        assert secrets["global-db"]["mode"] == "0600"

    def test_age_secrets_wired(self):
        data = nix_eval("eval-full.nix", "config.age.secrets")
        assert len(data) == 4
        assert "/var/secrets/sys-key.age" in str(data["sys-key"]["file"])

    def test_age_identity_paths_wired(self):
        data = nix_eval("eval-full.nix", "config.age.identityPaths")
        assert len(data) == 2
        assert "/etc/ssh/ssh_host_ed25519_key" in data

    def test_flake_root_passthrough(self):
        data = nix_eval("eval-full.nix", "config.agenixManager.cliConfig")
        assert data["flakeRoot"] == "/home/user/config"

    def test_secrets_path_passthrough(self):
        data = nix_eval("eval-full.nix", "config.agenixManager.cliConfig")
        assert data["secretsPath"] == "/var/secrets"


class TestNixEvalAppendedSecrets:
    def test_secrets_append_not_overwrite(self):
        data = nix_eval("eval-appended-secrets.nix")
        assert len(data["secrets"]) == 2
        names = {s["name"] for s in data["secrets"]}
        assert names == {"from-first", "from-second"}

    def test_appended_secrets_keep_individual_keys(self):
        data = nix_eval("eval-appended-secrets.nix")
        by_name = {s["name"]: s for s in data["secrets"]}
        assert by_name["from-first"]["keys"] == "users"
        assert by_name["from-second"]["keys"] == "systems"


class TestNixEvalMultipleKeys:
    def test_system_key_count(self):
        data = nix_eval("eval-multiple-keys-per-scope.nix")
        assert len(data["keys"]["systems"]) == 3

    def test_user_key_count(self):
        data = nix_eval("eval-multiple-keys-per-scope.nix")
        assert len(data["keys"]["users"]) == 2

    def test_other_key_count(self):
        data = nix_eval("eval-multiple-keys-per-scope.nix")
        assert len(data["keys"]["other"]) == 1

    def test_all_is_sum_of_scopes(self):
        data = nix_eval("eval-multiple-keys-per-scope.nix")
        keys = data["keys"]
        expected = keys["systems"] + keys["users"] + keys["other"]
        assert keys["all"] == expected

    def test_secret_keys_match_scope(self):
        data = nix_eval("eval-multiple-keys-per-scope.nix")
        by_name = {s["name"]: s for s in data["secrets"]}
        assert by_name["host-key"]["keys"] == "systems"
        assert by_name["user-key"]["keys"] == "users"
        assert by_name["ci-key"]["keys"] == "other"
        assert by_name["all-key"]["keys"] == "all"

    def test_cli_config_roundtrip(self):
        data = nix_eval("eval-multiple-keys-per-scope.nix")
        cfg = NixConfig.model_validate(data)
        assert len(cfg.keys.systems) == 3
        assert len(cfg.secrets) == 4


class TestNixEvalErrors:
    def test_invalid_scope_throws(self):
        err = nix_eval_error(
            "eval-invalid-scope.nix",
            "config.system.activationScripts.agenixManagerSecretsNix.text",
        )
        assert "attribute 'nonexistent_scope' missing" in err
