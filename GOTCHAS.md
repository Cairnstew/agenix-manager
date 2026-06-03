# Gotchas

## agenix-manager

### secrets.nix must be git-tracked
Nix flakes only see files in the git working tree. After initial write by the
activation script, run `git add secrets/secrets.nix`.

### First run chicken-and-egg
On a fresh system, the activation script writes `secrets.nix` at activation
time — but agenix needs `secrets.nix` to decrypt secrets during activation.
On the very first deploy, run `agenix-manager sync` *before* `nixos-rebuild
switch` to pre-create `secrets.nix`.

### Private key paths must be strings, not Nix paths
`identities` must use `"/etc/ssh/..."` strings, not `./relative` paths, to avoid
copying private keys to the world-readable Nix store.

### nix eval requires impure mode
If `secretsPath` or `flakeRoot` are absolute paths outside the flake, add
`--impure` to the eval call. The CLI already does this by default. Use
`--config-file` as fallback.

### agenix -e opens $EDITOR
The TUI suspends Textual, shells out, then resumes. Textual's `suspend()`
context manager handles this correctly.

### Rekey requires all identity keys to be present
`agenix --rekey` needs at least one identity that can decrypt each existing
secret. If rekeying on a new host, ensure you have access to at least one
original identity.

### `all` is always derived
Never set `agenixManager.keys.all` directly; it is computed as
`systems ++ users ++ other`. Setting it has no effect and will be silently
ignored.

## uv2nix

### uv.lock required for evaluation
The flake won't evaluate without a `uv.lock`. Run `uv lock` to generate it.

### Don't use `uv run` inside the dev shell
The dev shell already makes all scripts available directly. `uv run` creates
its own venv, defeating uv2nix's provisioning.

### Don't filter sources at workspace root
Filter per-package instead. Filtering at root causes IFD and breaks editables.

### Python version mismatch
If `flake.nix` uses `pkgs.python3` but `pyproject.toml` says
`requires-python = ">=3.12"`, you may get interpreter incompatibilities.
Pin `python = pkgs.python312` in `flake.nix`.
