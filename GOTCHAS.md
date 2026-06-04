# Gotchas

## agenix-manager

### secrets.nix must be git-tracked
Nix flakes only see files in the git working tree. After initial write by the
activation script, run `git add secrets/secrets.nix`.

### .age files are safe to commit, but mark them binary
Encrypted `.age` files are safe to commit to a public repository — they can
only be decrypted by holders of the corresponding private key. However, every
rekey or re-encrypt produces different ciphertext (random nonce), so git diffs
are meaningless. A `.gitattributes` at the repo root with `*.age binary`
suppresses noisy diffs and prevents git from attempting broken auto-merges.

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

## Secrets manifest

### Manifest must be git-tracked
Nix flakes only see files in the git working tree. After creating or updating
`secrets-manifest.json`, run `git add secrets/secrets-manifest.json` before
`nixos-rebuild switch`. The `agenix-manager new` subcommand prints a reminder.

### Manifest path must be accessible to the Nix evaluator
`builtins.readFile` requires the manifest path to be in the Nix store or a
string path accessible to the evaluator. With flakes, `./secrets/secrets-manifest.json`
works naturally because it's in the flake source tree. If `secretsPath` is set to
an absolute runtime path outside the flake, `builtins.readFile` will fail. Use
`--impure` in such cases, or keep `secretsPath` relative to the flake root.

### Manifest is safe to commit
The manifest contains only metadata (secret names, key scopes, file permissions),
never plaintext secret values. It is safe to commit to a public repository.

### Atomic manifest writes
The manifest is written atomically (write to `.tmp`, then `os.replace`) to
avoid corruption if the process is killed mid-write. A corrupt manifest makes
all secrets inaccessible at the next `nixos-rebuild switch`. Never edit the
manifest file by hand while the CLI is running.

### age output format (stdin path)
`agenix -e` produces ASCII-armored `.age` files (`age -e -a`). The CLI's stdin
encryption path (`--stdin`) uses the same flags (`age -e -a`) to produce
compatible output. Agenix can read both ASCII-armored and binary `.age` files,
so mismatched formats are not a concern.

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
