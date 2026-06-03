{ config, lib, pkgs, ... }:
let
  cfg = config.agenixManager;

  resolveKeys = scope:
    if builtins.hasAttr scope cfg.keyGroups then cfg.keyGroups.${scope}
    else throw "agenixManager: unknown key scope '${scope}'";

  _manifestSecrets = let
    manifestPath = cfg.manifestPath;
  in
    if builtins.pathExists manifestPath then
      let
        raw = builtins.fromJSON (builtins.readFile manifestPath);
        entries = raw.secrets or [];
      in
        map (e:
          let
            resolvedKeys =
              if builtins.isList e.scope then e.scope
              else resolveKeys e.scope;
          in
          {
            name  = e.name;
            keys  = resolvedKeys;
            scope = if builtins.isList e.scope then "custom" else e.scope;
            owner = e.owner or "root";
            group = e.group or "root";
            mode  = e.mode or "0400";
          }
        ) entries
    else
      lib.warn ''
        agenixManager: No manifest found at ${manifestPath}.
        Run 'agenix-manager new' to create your first secret,
        or ensure the manifest is committed before nixos-rebuild switch.
      '' [];

  defaultKeyGroups = {
    systems = cfg.keys.systems;
    users   = cfg.keys.users;
    other   = cfg.keys.other;
    all     = cfg.keys.systems ++ cfg.keys.users ++ cfg.keys.other;
  };

  agenixManagerPackage = pkgs.python3Packages.buildPythonPackage {
    pname = "agenix-manager";
    version = "0.1.0";
    src = ../.;
    pyproject = true;
    build-system = [ pkgs.python3Packages.hatchling ];
    dependencies = with pkgs.python3Packages; [
      click
      textual
      rich
      pydantic
    ];
    doCheck = false;
    meta.description = "NixOS module + TUI CLI for declarative agenix secret management";
  };

in {
  options.agenixManager = {

    enable = lib.mkEnableOption "agenixManager declarative secrets";

    manifestPath = lib.mkOption {
      type = lib.types.str;
      default = cfg.secretsPath + "/secrets-manifest.json";
      defaultText = lib.literalMD "`<secretsPath>/secrets-manifest.json`";
      description = ''
        Path to the secrets manifest JSON file.
        The manifest is maintained by the agenix-manager CLI.
        Use a string path (not a Nix path literal) to avoid Nix store resolution.
        If the file does not exist (bootstrap), secrets are empty and a
        warning is emitted instructing the user to run 'agenix-manager new'.
      '';
    };

    secretsPath = lib.mkOption {
      type = lib.types.str;
      description = ''
        Absolute path to the directory containing .age files.
        Use a string path (not a Nix path literal) to avoid
        having Nix resolve it to the read-only store.
        Example: "/etc/secrets".
      '';
    };

    keys = {
      systems = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [];
        description = "SSH public keys for NixOS host system identities (ssh_host_ed25519_key.pub content)";
      };
      users = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [];
        description = "SSH public keys for human user identities";
      };
      other = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [];
        description = "SSH public keys for any other identity (CI, hardware tokens, etc.)";
      };
    };

    keyGroups = lib.mkOption {
      type = lib.types.attrsOf (lib.types.listOf lib.types.str);
      default = defaultKeyGroups;
      defaultText = lib.literalMD "`{ systems = cfg.keys.systems; users = cfg.keys.users; other = cfg.keys.other; }`";
      description = ''
        Named key groups for secret encryption scopes.
        Built-in groups (systems, users, other) are defined automatically.
        Additional groups can be added for custom scopes:

        ```
        agenixManager.keyGroups = {
          deployment = cfg.keys.systems ++ [ "ssh-ed25519 AAAA..." ];
        };
        ```
      '';
    };

    identities = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [];
      description = ''
        Runtime paths to SSH private keys used for decryption.
        These are passed to age.identityPaths. Use string paths (not
        Nix paths) to avoid copying private keys to the Nix store.
        Example: [ "/etc/ssh/ssh_host_ed25519_key" ]
      '';
    };

    package = lib.mkOption {
      type = lib.types.package;
      default = agenixManagerPackage;
      defaultText = lib.literalMD "Built from source";
      description = "The agenix-manager package to install.";
    };

    cliConfig = lib.mkOption {
      internal = true;
      readOnly = true;
      type = lib.types.attrs;
      description = "Computed CLI configuration for agenix-manager CLI consumption via nix eval";
    };

    secretsNixContent = lib.mkOption {
      internal = true;
      readOnly = true;
      type = lib.types.str;
      description = "Computed secrets.nix content for drift checking and activation.";
    };

  };

  config = lib.mkIf cfg.enable {

    age.secrets = lib.listToAttrs (map (s: lib.nameValuePair s.name {
      file  = "${cfg.secretsPath}/${s.name}.age";
      owner = s.owner;
      group = s.group;
      mode  = s.mode;
    }) _manifestSecrets);

    age.identityPaths = cfg.identities;

    environment.systemPackages = [ cfg.package ];

    agenixManager.secretsNixContent = let
      renderKeyList = keys:
        "[ " + (lib.concatMapStringsSep " " (k: "\"${k}\"") keys) + " ]";
      renderEntry = s:
        "  \"${s.name}.age\".publicKeys = ${renderKeyList s.keys};";
      entries = lib.concatStringsSep "\n" (map renderEntry _manifestSecrets);
    in ''
      # Auto-generated by agenixManager NixOS module — do not edit by hand.
      # Regenerated on every nixos-rebuild switch.
      {
      ${entries}
      }
    '';

    system.activationScripts.agenixManagerSecretsNix = let
      secretsNixFile = pkgs.writeText "secrets.nix" cfg.secretsNixContent;
      cliConfigFile = pkgs.writeText "agenix-manager-cache.json" (builtins.toJSON cfg.cliConfig);
      keysSnapshotFile = pkgs.writeText "keys-snapshot.json" (
        builtins.toJSON (lib.listToAttrs (map (s:
          lib.nameValuePair s.name s.keys
        ) _manifestSecrets))
      );
    in {
      text = ''
        echo "[agenixManager] Writing secrets.nix -> /etc/agenix/secrets.nix"
        echo "[agenixManager] Writing CLI cache   -> /etc/agenix/agenix-manager-cache.json"
        echo "[agenixManager] Writing keys snapshot -> /etc/agenix/keys-snapshot.json"
        mkdir -p /etc/agenix
        cp ${secretsNixFile} /etc/agenix/secrets.nix
        cp ${cliConfigFile} /etc/agenix/agenix-manager-cache.json
        cp ${keysSnapshotFile} /etc/agenix/keys-snapshot.json
        chmod 644 /etc/agenix/agenix-manager-cache.json /etc/agenix/keys-snapshot.json
      '';
      deps = [];
    };

    agenixManager.cliConfig = {
      secretsPath      = cfg.secretsPath;
      secretsNixPath   = "/etc/agenix/secrets.nix";
      keysSnapshotPath = "/etc/agenix/keys-snapshot.json";
      identities       = cfg.identities;
      keys             = cfg.keyGroups // { all = cfg.keyGroups.systems ++ cfg.keyGroups.users ++ cfg.keyGroups.other; };
      secrets = map (s: {
        inherit (s) name owner group mode scope keys;
        file  = "${cfg.secretsPath}/${s.name}.age";
      }) _manifestSecrets;
    };

  };
}
