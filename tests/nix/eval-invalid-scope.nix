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
        keys.users = [ "ssh-ed25519 AAAA...u" ];
        secrets = [{ name = "bad"; keys = "nonexistent_scope"; }];
      };
    })
  ];
  specialArgs = { inherit pkgs; };
}
