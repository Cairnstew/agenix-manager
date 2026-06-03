# Project Structure

```
.
├── flake.nix                 # Nix flake — thin orchestrator
├── flake.lock                # Nix lock file
├── pyproject.toml            # Python project metadata
├── uv.lock                   # uv lock file
├── .python-version           # "3.12"
│
├── nix/
│   ├── default.nix           # Package derivation (mkApplication)
│   ├── module.nix            # NixOS agenixManager module
│   ├── devshell.nix          # Dev shells (default + bootstrap)
│   ├── overlay.nix           # pkgs overlay reference
│   ├── home-module.nix       # Home Manager module
│   └── checks.nix            # Flake checks
│
├── src/
│   └── agenix_manager/       # Application package
│       ├── __init__.py
│       ├── __main__.py       # python -m agenix_manager
│       ├── cli.py            # Click entrypoint
│       ├── config.py         # NixConfig, nix eval, JSON load
│       ├── state.py          # SecretState, scan, missing detection
│       ├── secrets_nix.py    # secrets.nix generation
│       ├── ops/              # Subprocess wrappers
│       │   ├── encrypt.py
│       │   ├── decrypt.py
│       │   └── rekey.py
│       └── tui/              # Textual TUI
│           ├── app.py
│           ├── screens/
│           │   ├── main_menu.py
│           │   ├── status.py
│           │   ├── encrypt.py
│           │   ├── decrypt.py
│           │   └── rekey.py
│           └── widgets/
│               ├── secret_table.py
│               └── key_panel.py
│
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_state.py
│   ├── test_secrets_nix.py
│   ├── test_ops.py
│   └── fixtures/
│       └── data/
│           └── sample_config.json
│
├── AGENTS.md
├── GOTCHAS.md
├── HEATMAP.md
├── STRUCTURE.md
├── README.md
└── CHANGELOG.md
```
