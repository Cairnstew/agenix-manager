{ config, lib, pkgs, agenixPackage ? null, ... }:
let
  cfg = config.agenixManager;

  # All user-defined groups plus computed "all" = union of all groups
  computedGroups = cfg.keys.groups // {
    all = lib.foldl' (acc: g: acc ++ g) [] (builtins.attrValues cfg.keys.groups);
  };

  resolveKeys = scope:
    if builtins.hasAttr scope computedGroups then computedGroups.${scope}
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
          let
            # If e.hosts is present but not a list (e.g. a stray string),
            # silently treat as null (all hosts) rather than erroring.
            # Malformed hosts disables filtering rather than breaking eval.
            rawHosts = e.hosts or null;
          in {
            name  = e.name;
            keys  = resolvedKeys;
            scope = if builtins.isList e.scope then "custom" else e.scope;
            owner = e.owner or "root";
            group = e.group or "root";
            mode  = e.mode or "0400";
            hosts = if builtins.isList rawHosts then rawHosts else null;
          }
        ) entries
    else
      lib.warn ''
        agenixManager: No manifest found at ${manifestPath}.
        Run 'agenix-manager new' to create your first secret,
        or ensure the manifest is committed before nixos-rebuild switch.
      '' [];

  # Apply host constraints and excludedSecrets overrides.
  # Order: declarative intent (hosts) first, then per-host override (excludedSecrets).
  _filteredManifestSecrets = let
    hostMatch = s:
      if s.hosts != null
      then builtins.elem config.networking.hostName s.hosts
      else true;
    notExcluded = s: !builtins.elem s.name cfg.excludedSecrets;
  in builtins.filter (s: hostMatch s && notExcluded s) _manifestSecrets;

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
      default = "${cfg.secretsPath}/secrets-manifest.json";
      defaultText = lib.literalMD "`<secretsPath>/secrets-manifest.json`";
      description = ''
        Path to the secrets manifest JSON file.
        The manifest is maintained by the agenix-manager CLI.
        If the file does not exist (bootstrap), secrets are empty and a
        warning is emitted instructing the user to run 'agenix-manager new'.
      '';
    };

    secretsPath = lib.mkOption {
      type = lib.types.path;
      description = ''
        Path to the directory containing .age files.
        Typically set as a Nix path literal (e.g. ./secrets).
        Nix resolves these to the store during evaluation, but
        the CLI automatically maps them back to the real path
        at runtime using the flake root.
        Example: ./secrets.
      '';
    };

    keys.groups = lib.mkOption {
      type = lib.types.attrsOf (lib.types.listOf lib.types.str);
      default = {};
      description = ''
        Named key groups for secret encryption scopes.
        Each group is a list of SSH public key strings.
        The "all" group is automatically computed as the union of all groups.

        ```
        agenixManager.keys.groups = {
          systems = [ "ssh-ed25519 AAAA..." ];
          users   = [ "ssh-ed25519 AAAA..." ];
          deployment = [ "ssh-ed25519 AAAA..." ];
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

    excludedSecrets = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [];
      description = ''
        Secrets to exclude from age.secrets registration on this host.
        This is a per-host override — use when a secret's `hosts` field (if any)
        does not provide the granularity you need, or to temporarily disable a
        secret without modifying the manifest.
      '';
    };

    package = lib.mkOption {
      type = lib.types.package;
      default = agenixManagerPackage;
      defaultText = lib.literalMD "Built from source";
      description = "The agenix-manager package to install.";
    };

    agenixPackage = lib.mkOption {
      type = lib.types.nullOr lib.types.package;
      default = agenixPackage;
      defaultText = lib.literalMD "The agenix package from the flake input";
      description = ''
        The agenix package providing the ``agenix`` binary used by the
        ``agenix-manager`` CLI for encryption / decryption operations.

        When unset (``null``), the CLI falls back to ``$PATH`` lookup
        and a set of well-known NixOS paths.  Set this to the agenix
        package from the agenix flake input to guarantee the binary is
        found without relying on ``environment.systemPackages``.
      '';
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
    }) _filteredManifestSecrets);

    age.identityPaths = cfg.identities;

    environment.systemPackages = [ cfg.package pkgs.age ];

    agenixManager.secretsNixContent = let
      renderKeyList = keys:
        "[ " + (lib.concatMapStringsSep " " (k: "\"${k}\"") keys) + " ]";
      renderEntry = s:
        "  \"${s.name}.age\".publicKeys = ${renderKeyList s.keys};";
      entries = lib.concatStringsSep "\n" (map renderEntry _filteredManifestSecrets);
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
        ) _filteredManifestSecrets))
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
      secretsPath      = toString cfg.secretsPath;
      secretsNixPath   = "/etc/agenix/secrets.nix";
      keysSnapshotPath = "/etc/agenix/keys-snapshot.json";
      agenixBin        = if cfg.agenixPackage != null then "${cfg.agenixPackage}/bin/agenix" else null;
      identities       = cfg.identities;
      keys = computedGroups;
      secrets = map (s: {
        inherit (s) name owner group mode scope keys;
        file  = "${toString cfg.secretsPath}/${s.name}.age";
      }) _filteredManifestSecrets;
    };

  };
}
