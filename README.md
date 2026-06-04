# agenix-manager

NixOS module + TUI CLI for declarative agenix secret management.

Secrets are declared in a **JSON manifest file** (`secrets/secrets-manifest.json`)
managed by the CLI — never in Nix directly. The Nix module reads the manifest at
eval time and wires up `config.age.secrets.*` automatically.

## Features

- **Declarative** — secrets declared in a JSON manifest, never in Nix
- **Multi-key** — encrypt secrets for host keys, user keys, CI keys, or any
  combination via named key groups
- **Automatic wiring** — `config.age.secrets.*` generated from the manifest
- **TUI** — status overview, create/edit/decrypt/rekey/remove operations via
  keyboard-driven interface
- **CLI** — headless operation for scripting and CI

## NixOS module

```nix
# flake.nix
{
  inputs.agenix.url = "github:ryantm/agenix";
  inputs.agenix-manager.url = "github:Cairnstew/agenix-manager";

  outputs = { agenix, agenix-manager, nixpkgs, ... }: {
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      modules = [
        agenix.nixosModules.default
        agenix-manager.nixosModules.default
        {
          agenixManager = {
            enable      = true;
            secretsPath = ./secrets;

            keys.systems = [ "ssh-ed25519 AAAA...hostkey" ];
            keys.users   = [ "ssh-ed25519 AAAA...seankey" ];

            # Optional custom key groups:
            # keyGroups.deployment = cfg.keys.systems ++ [ "ssh-ed25519 AAAA...ci-key" ];

            identities = [ "/etc/ssh/ssh_host_ed25519_key" ];
          };
        }
      ];
    };
  };
}
```

The module automatically adds both the `agenix-manager` CLI and `age` to
`environment.systemPackages` — no extra config needed. Just import and enable.

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
sudo nix run github:Cairnstew/agenix-manager -- new --name my-secret --scope users --stdin <<< "myvalue"
```

If you already have the CLI installed:

```bash
agenix-manager new --name my-secret --scope users --stdin <<< "myvalue"
```

Interactive wizard (recommended for first use):

```bash
sudo nix run github:Cairnstew/agenix-manager -- new
```

Then commit everything and rebuild:

```bash
git add secrets/
nixos-rebuild switch --flake .#myhost
```

The repository includes a `.gitattributes` marking `*.age` files as binary
(they change entirely on every rekey due to the random nonce) and a
`secrets/.gitkeep` so the directory is present on clone.

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
sudo nix run github:Cairnstew/agenix-manager -- new
sudo nix run github:Cairnstew/agenix-manager -- status
```

> `sudo` is needed because `agenix-manager` writes to `/etc/agenix/` and
> reads from the Nix daemon. If your user is in the `trusted-users` set and
> has write access to the secrets directory, `sudo` can be omitted.

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

A 4-step fully keyboard-driven wizard:

1. **Secret name** — type a name, `Enter` to confirm
2. **Key scope** — arrow keys to navigate, `Space` to toggle, `Ctrl+Enter` to
   confirm (selecting multiple scopes encrypts for all of them)
3. **Permissions** — `Tab` between owner/group/mode fields, `Enter` to confirm
4. **Secret value** — type or paste multi-line content, `Ctrl+Enter` to create

`Esc` goes back one step at any point.

On completion: writes the manifest, regenerates `secrets.nix`, encrypts the
value, and prints a reminder to `git add secrets/`.

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

### Activation and cache

Every `nixos-rebuild switch`:

1. Writes `secrets.nix` to `/etc/agenix/`
2. Writes a JSON CLI cache to `/etc/agenix/agenix-manager-cache.json`
3. Writes a keys snapshot to `/etc/agenix/keys-snapshot.json`

The CLI reads from the cache on startup — instant, no `nix eval` overhead.
Falls back to `nix eval` if the cache is missing (e.g. before first activation).

### TUI

The main interface is a single **status screen** showing key group counts and the
secret table (name, scope, status, owner, mode). All operations are available via
hotkeys — no menu navigation.

| Key | Operation | Description |
|---|---|---|
| `n` | **New** | Opens the 4-step wizard to create a secret |
| `e` | **Encrypt** | Re-encrypt the selected secret via `$EDITOR` |
| `d` | **Decrypt** | Shows decrypted plaintext in an ephemeral viewer |
| `r` | **Rekey** | Shows key diff confirmation, then re-encrypts with current keys |
| `R` | **Remove** | Deletes the `.age` file and removes the secret from the manifest |
| `q` | **Quit** | Exit the TUI |

The status screen reads from a cache file (`/etc/agenix/agenix-manager-cache.json`)
on startup for instant loading. If the cache is missing, it falls back to
`nix eval` to compute the config.

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
