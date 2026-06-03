.PHONY: test test-py test-nix test-all test-cli

test:
	nix develop .#bootstrap -c uv run pytest tests/ -v

test-py:
	nix develop .#bootstrap -c uv run pytest tests/ -v -m "not slow"

test-nix:
	nix flake check

test-all: test-py test-nix

test-cli:
	CLI_TESTS=1 nix develop .#bootstrap -c uv run pytest tests/test_cli_integration.py -v

test-eval:
	nix develop .#bootstrap -c uv run pytest tests/test_nix_eval.py -v

test-vm:
	nix build .#vmTests.$$(nix eval --raw --impure --expr builtins.currentSystem).basic -L

test-vm-all:
	for scenario in basic multi-secret custom-perms user-keys; do \
		nix build .#vmTests.$$(nix eval --raw --impure --expr builtins.currentSystem).$$scenario -L; \
	done
