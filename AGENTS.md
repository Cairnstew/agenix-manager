# Agent Instructions

## About this project

NixOS module + TUI CLI for declarative agenix secret management. Python project managed with `uv2nix`.

## Key files

| File | Role |
|---|---|
| `flake.nix` | Nix flake — thin orchestrator, delegates to `nix/` modules |
| `nix/default.nix` | Package derivation (mkApplication) |
| `nix/devshell.nix` | Dev shell definitions (default + bootstrap) |
| `nix/overlay.nix` | pkgs overlay reference |
| `nix/module.nix` | NixOS agenixManager module |
| `nix/home-module.nix` | Home Manager module (user env) |
| `nix/checks.nix` | Flake checks |
| `pyproject.toml` | Python project metadata, dependencies |
| `uv.lock` | Lock file — drives the Nix overlay |
| `src/agenix_manager/` | Application package source |
| `tests/` | Test suite |

## Rules for agents

1. **Never edit `uv.lock` directly** — always use `uv lock` or `uv add`/`uv remove`.
2. **After editing `pyproject.toml`**, tell the user to run `uv lock` to regenerate `uv.lock`.
3. **After editing `flake.nix`**, run `nix flake lock` to update `flake.lock`.
4. **Python version**: 3.12 — keep `requires-python` in `pyproject.toml` and `python = pkgs.python312` in `flake.nix` in sync.
5. **Hatchling backend**: `pyproject.toml` uses `hatchling.build_meta`. If switching backends, update `build-system.requires` accordingly.
6. **secrets.nix must be git-tracked**: After first write by activation script, run `git add secrets/secrets.nix`.
7. **First run chicken-and-egg**: Run `agenix-manager sync` *before* first `nixos-rebuild switch` to pre-create `secrets.nix`.
8. **Private key paths**: Use string paths (e.g. `"/etc/ssh/..."`) not Nix paths to avoid copying private keys to the Nix store.
