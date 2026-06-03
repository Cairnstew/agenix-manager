let
  pkgs = import <nixpkgs> {};
  lib = pkgs.lib;
  manifestPath = toString ./. + "/eval-age-wiring-manifest.json";
  nixos = import <nixpkgs/nixos/lib/eval-config.nix> {
    inherit pkgs;
    modules = [
      { options.age.secrets = lib.mkOption { type = lib.types.attrsOf lib.types.raw; default = {}; };
        options.age.identityPaths = lib.mkOption { type = lib.types.listOf lib.types.str; default = []; };
      }
      ({ config, lib, ... }: {
        imports = [ ../../nix/module.nix ];
        agenixManager = {
          enable = true;
          secretsPath = "/secrets";
          manifestPath = manifestPath;
          keys.systems = [ "ssh-ed25519 AAAA...test" ];
          keys.users = [ "ssh-ed25519 AAAA...userkey" ];
          identities = [ "/etc/ssh/ssh_host_ed25519_key" ];
        };
      })
    ];
  };
in
nixos.config
