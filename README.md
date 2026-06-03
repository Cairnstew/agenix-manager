# agenix-manager

NixOS module + TUI CLI for declarative agenix secret management.

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

    secrets = [
      { name = "github-token"; keys = "users"; }
      { name = "db-password";  keys = "all";   owner = "postgres"; }
      # Literal key lists also work (resolved at the Nix level):
      # { name = "deploy-token"; keys = [ "ssh-ed25519 AAAA..." ]; }
    ];
  };
}
```

### Key groups and scopes

Each secret has a `keys` option that accepts either a **scope name** or a **literal list of SSH public keys**.

Scope names resolve to named key groups:

| Scope | Resolution |
|---|---|
| `"all"` | `systems ++ users ++ other` |
| `"systems"` | `agenixManager.keys.systems` |
| `"users"` | `agenixManager.keys.users` |
| `"other"` | `agenixManager.keys.other` |
| `"deployment"` | Custom — defined in `agenixManager.keyGroups` |

Scope names are resolved to key lists at the Nix module boundary before being
emitted in `cliConfig`. The Python CLI always sees resolved `list[str]` and
never needs to know about scope names — the original scope is preserved in a
`scope` field for display purposes only.

### Bootstrap and cache

On first deploy, run `agenix-manager sync` before `nixos-rebuild switch` to
pre-create `secrets.nix`. After that, every `nixos-rebuild switch`:

1. Writes `secrets.nix` to `/etc/agenix/`
2. Writes a JSON CLI cache to `/etc/agenix/agenix-manager-cache.json`
3. Writes a keys snapshot to `/etc/agenix/keys-snapshot.json`

The CLI reads from the cache on startup — instant, no `nix eval` overhead.
Falls back to `nix eval` if the cache is missing (e.g. before first activation).

## CLI

```bash
agenix-manager                       # full TUI
agenix-manager status                # status table only
agenix-manager sync                  # re-sync secrets.nix without TUI
agenix-manager --host myhost         # eval config for another host
agenix-manager --flake /path/to/flake  # explicit flake reference
agenix-manager --config-file config.json  # skip nix eval, use JSON file
```

### TUI screens

| Screen | Binding | Description |
|---|---|---|
| **Status** | — | Key group counts + secret table (scope, status, owner, mode) |
| **Encrypt** | `e` | Suspends TUI, opens `$EDITOR` via `agenix -e`, resumes |
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
