# Project Structure

```
.
├── flake.nix                 # Nix flake — thin orchestrator
├── flake.lock                # Nix lock file
├── pyproject.toml            # Python project metadata
├── uv.lock                   # uv lock file
├── .python-version           # "3.12"
├── .gitattributes            # *.age binary diff/merge config
│
├── secrets/                  # Secrets directory (git-tracked)
│   └── .gitkeep              # Ensures directory exists on clone
│
├── nix/
│   ├── default.nix           # Package derivation (mkApplication)
│   ├── module.nix            # NixOS agenixManager module (+ pkgs.age)
│   ├── devshell.nix          # Dev shells (default + bootstrap)
│   ├── overlay.nix           # pkgs overlay reference
│   ├── home-module.nix       # Home Manager module (+ pkgs.age)
│   ├── checks.nix            # Flake checks
│   └── vm-tests.nix          # NixOS VM integration tests
│
├── src/
│   └── agenix_manager/       # Application package
│       ├── __init__.py
│       ├── __main__.py       # python -m agenix_manager
│       ├── cli.py            # Click entrypoint
│       ├── config.py         # NixConfig, nix eval, JSON load
│       ├── state.py          # SecretState, scan, missing detection
│       ├── secrets_nix.py    # secrets.nix generation
│       ├── manifest.py       # Manifest load/save/add/remove/resolve
│       ├── ops/              # Subprocess wrappers
│       │   ├── encrypt.py
│       │   ├── decrypt.py
│       │   ├── rekey.py
│       │   └── remove.py
│       └── tui/              # Textual TUI
│           ├── app.py
│           ├── actions.py    # ActionHandler classes (New/Encrypt/Decrypt/Rekey/Remove)
│           ├── base.py       # Screen base classes (TableScreen, WizardScreen, modals)
│           ├── screens/
│           │   ├── status.py       # Main status screen with hotkeys
│           │   ├── new_secret.py   # 4-step keyboard-driven wizard
│           │   ├── rekey_confirm.py # Rekey key-diff confirmation modal
│           │   └── decrypt_view.py # Ephemeral plaintext viewer modal
│           └── widgets/
│               ├── secret_table.py
│               └── key_panel.py
│
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_state.py
│   ├── test_secrets_nix.py
│   ├── test_manifest.py
│   ├── test_ops.py
│   ├── test_cli_integration.py
│   ├── test_nix_eval.py
│   ├── test_encrypt_stdin.py
│   ├── nix/                  # Nix eval fixtures
│   │   ├── eval-simple.nix
│   │   ├── eval-full.nix
│   │   ├── eval-multiple-keys-per-scope.nix
│   │   ├── eval-missing-manifest.nix
│   │   └── eval-invalid-scope.nix
│   └── nixos/                # NixOS VM test fixtures
│       ├── common.nix
│       └── scenarios/
│
├── .github/workflows/        # CI / CD
│   ├── ci.yml                # Lint, typecheck, test (PRs + release tags)
│   ├── vm-test.yml           # NixOS VM integration tests (PRs + release tags + manual)
│   ├── release.yml           # Build & publish on v* tags
│   └── update-flake-lock.yml # Weekly automated flake.lock bump
│
├── AGENTS.md
├── GOTCHAS.md
├── HEATMAP.md
├── STRUCTURE.md
├── README.md
└── CHANGELOG.md
```
