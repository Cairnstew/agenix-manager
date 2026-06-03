let
  pkgs = import <nixpkgs> {};
  lib = pkgs.lib;
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
          keys.systems = [ "ssh-ed25519 AAAA...test" ];
          keys.users = [ "ssh-ed25519 AAAA...userkey" ];
          identities = [ "/etc/ssh/ssh_host_ed25519_key" ];
          secrets = [
            { name = "t1"; keys = "systems"; owner = "root"; group = "root"; mode = "0400"; }
            { name = "t2"; keys = "all"; owner = "postgres"; group = "postgres"; mode = "0600"; }
          ];
        };
      })
    ];
  };
in
nixos.config
