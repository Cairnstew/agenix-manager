# Complexity/Fragility Heatmap

| File | Score | Rationale |
|---|:---:|---|
| `flake.nix` | 🔴 High | Central orchestration, multiple inputs, overlays, pythonSets |
| `nix/module.nix` | 🔴 High | Full option schema, activation script, cliConfig export |
| `nix/default.nix` | 🟢 Low | Simple mkApplication wrapper |
| `nix/devshell.nix` | 🟡 Medium | DevShell definitions |
| `nix/checks.nix` | 🟢 Low | Build smoke tests |
| `pyproject.toml` | 🟡 Medium | Changes with dependency adds |
| `src/agenix_manager/config.py` | 🟡 Medium | Nix eval, Pydantic models |
| `src/agenix_manager/state.py` | 🟢 Low | Simple state computation |
| `src/agenix_manager/secrets_nix.py` | 🟢 Low | Template rendering |
| `src/agenix_manager/cli.py` | 🟡 Medium | Entrypoint, command dispatch |
| `src/agenix_manager/tui/` | 🟡 Medium | Textual app, screens, widgets |
| `src/agenix_manager/ops/` | 🟢 Low | Subprocess wrappers |
| `tests/` | 🟢 Low | Test suite |
