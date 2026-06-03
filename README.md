# agenix-manager

NixOS module + TUI CLI for declarative agenix secret management.

## Usage

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
    flakeRoot   = ./.;

    keys.systems = [ "ssh-ed25519 AAAA...hostkey" ];
    keys.users   = [ "ssh-ed25519 AAAA...seankey" ];

    identities = [ "/etc/ssh/ssh_host_ed25519_key" ];

    secrets = [
      { name = "github-token"; keys = "users"; }
      { name = "db-password";  keys = "all";   owner = "postgres"; }
    ];
  };
}
```

## CLI

```bash
agenix-manager              # full TUI
agenix-manager status       # status table only
agenix-manager sync         # re-sync secrets.nix without TUI
agenix-manager --host myhost  # if running from another host
agenix-manager --config-file config.json  # skip nix eval, use JSON
```
