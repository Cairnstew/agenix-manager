# agenix-manager

NixOS module + TUI CLI for declarative agenix secret management.

Secrets are declared in a **JSON manifest file** (`secrets/secrets-manifest.json`)
managed by the CLI — never in Nix directly. The Nix module reads the manifest at
eval time and wires up `config.age.secrets.*` automatically.

## NixOS module

```nix
# flake.nix inputs
inputs.agenix-manager.url = "github:Cairnstew/agenix-manager";
inputs.agenix.url = "github:ryantm/agenix";

# configuration.nix
{ inputs, ... }: {
  imports = [
    inputs.agenix.nixosModules.default
    inputs.agenix-manager.nixosModules.default
  ];

  agenixManager = {
    enable      = true;
    secretsPath = ./secrets;

    keys.systems = [ "ssh-ed25519 AAAA...hostkey" ];
    keys.users   = [ "ssh-ed25519 AAAA...seankey" ];

    # Optional custom key groups beyond the three built-in scopes:
    # keyGroups.deployment = cfg.keys.systems ++ [ "ssh-ed25519 AAAA...ci-key" ];

    identities = [ "/etc/ssh/ssh_host_ed25519_key" ];
  };
}
```

Secrets are **not** declared in Nix — they live in the manifest. After adding
your first secret (see CLI section below), reference them from other modules
as usual:

```nix
{ config, ... }: {
  users.users.sean = {
    passwordFile = config.age.secrets.github-token.path;
  };
}
```

### Manifest file

Created and maintained by `agenix-manager new`. Format:

```json
{
  "version": 1,
  "secrets": [
    {
      "name": "github-token",
      "scope": "users",
      "owner": "root",
      "group": "root",
      "mode": "0400"
    },
    {
      "name": "db-password",
      "scope": "all",
      "owner": "postgres",
      "group": "postgres",
      "mode": "0400"
    }
  ]
}
```

The manifest contains only **metadata** (names, scopes, permissions) — never
plaintext values. It is safe to commit to a public repository, but must be
committed before `nixos-rebuild switch` sees it.

### Bootstrap

On a fresh system, the manifest does not yet exist. The Nix module emits a
warning and produces an empty secrets list.

If you haven't added `agenix-manager` to your system packages yet, run it
directly from the flake:

```bash
nix run github:Cairnstew/agenix-manager -- new --name my-secret --scope users --stdin <<< "myvalue"
```

If you already have the CLI installed (e.g. via the Home Manager module or
`environment.systemPackages`):

```bash
agenix-manager new --name my-secret --scope users --stdin <<< "myvalue"
```

Interactive wizard (recommended for first use):

```bash
nix run github:Cairnstew/agenix-manager -- new
```

Then commit the manifest and `.age` file, and rebuild:

```bash
git add secrets/
nixos-rebuild switch --flake .#myhost
```

See CLI section for all options.

### Key groups and scopes

Each secret in the manifest has a `scope` field that accepts either a **scope
name** or a **literal list of SSH public keys**.

Scope names resolve to named key groups:

| Scope | Resolution |
|---|---|
| `"all"` | `systems ++ users ++ other` |
| `"systems"` | `agenixManager.keys.systems` |
| `"users"` | `agenixManager.keys.users` |
| `"other"` | `agenixManager.keys.other` |
| `"deployment"` | Custom — defined in `agenixManager.keyGroups` |

Scope names are resolved to key lists by both the Nix module (at eval time)
and the Python CLI (at manifest load time). The original scope is preserved
in a `scope` field for display purposes.

## CLI

From the flake directly (no install required):

```bash
nix run github:Cairnstew/agenix-manager -- new
nix run github:Cairnstew/agenix-manager -- status
```

If installed on your system:

```bash
agenix-manager                       # full TUI
agenix-manager new                   # interactive TUI wizard
agenix-manager new --name my-secret --scope users --stdin <<< "myvalue"
agenix-manager status                # status table only
agenix-manager sync                  # re-sync secrets.nix without TUI
agenix-manager --config-file config.json  # skip nix eval, use JSON file
```

### `agenix-manager new`

Creates a new secret — the primary entry point for secret management.

**Interactive wizard** (no flags):

```bash
agenix-manager new
```

Walks through three steps:
1. Enter secret name (validated: alphanumeric, hyphens, underscores)
2. Select key scope from available groups (with member counts)
3. Set owner, group, mode (defaults: root, root, 0400)

On completion: writes the manifest, regenerates `secrets.nix`, opens `$EDITOR`
via `agenix -e` for the secret value.

**Non-interactive** (all flags provided):

```bash
# From editor (opens $EDITOR):
agenix-manager new --name github-token --scope users

# From stdin (piped, no editor):
echo "mysecret" | agenix-manager new --name github-token --scope users --stdin
```

Options:

| Flag | Default | Description |
|---|---|---|
| `--name` | — | Secret name (required for non-interactive) |
| `--scope` | — | Key scope (`all`, `systems`, `users`, `other`, or custom) |
| `--owner` | `root` | File owner |
| `--group` | `root` | File group |
| `--mode` | `0400` | File mode (octal) |
| `--stdin` | — | Read plaintext from stdin instead of opening editor |

After creation, a reminder is printed to `git add` the manifest and `.age` file
before rebuilding.

### Activation and cache

Every `nixos-rebuild switch`:

1. Writes `secrets.nix` to `/etc/agenix/`
2. Writes a JSON CLI cache to `/etc/agenix/agenix-manager-cache.json`
3. Writes a keys snapshot to `/etc/agenix/keys-snapshot.json`

The CLI reads from the cache on startup — instant, no `nix eval` overhead.
Falls back to `nix eval` if the cache is missing (e.g. before first activation).

### TUI screens

| Screen | Binding | Description |
|---|---|---|
| **Status** | — | Key group counts + secret table (scope, status, owner, mode) |
| **New secret** | — | 3-step wizard (name, scope, permissions) |
| **Encrypt** | `e` | Re-encrypt/edit an existing secret via `agenix -e` |
| **Decrypt** | `d` | Shows plaintext in ephemeral viewer (never written to disk) |
| **Rekey** | `r` | Shows key diff confirmation before re-encrypting |
| **Remove** | `d` | Deletes `.age` file (irreversible) |

The rekey screen reads the on-disk keys snapshot to show current recipients vs
new recipients, highlighting added (green) and removed (red) keys. If no keys
changed, it warns and asks for confirmation anyway.

## Development

```bash
nix develop
# or for a minimal shell:
nix develop .#bootstrap
```

Tests run via pytest (requires the dev shell or a virtualenv):

```bash
.venv/bin/python -m pytest tests/
```
