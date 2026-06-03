let
  pkgs = import <nixpkgs> {};
  lib = pkgs.lib;
in
lib.evalModules {
  modules = [
    (import ./stub-options.nix { inherit lib; })
    ({ config, lib, pkgs, ... }: {
      imports = [ ../../nix/module.nix ];
      agenixManager = {
        enable = true;
        secretsPath = "/secrets";
        flakeRoot = "/etc/nixos";
        keys.users   = [ "ssh-ed25519 AAAA...u" ];
        keys.systems = [ "ssh-ed25519 AAAA...s" ];
      };
    })
    { agenixManager.secrets = [{ name = "from-first"; keys = "users"; }]; }
    { agenixManager.secrets = [{ name = "from-second"; keys = "systems"; }]; }
  ];
  specialArgs = { inherit pkgs; };
}
