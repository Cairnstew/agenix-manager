let
  pkgs = import <nixpkgs> {};
  lib = pkgs.lib;
  manifestPath = toString ./. + "/eval-invalid-scope-manifest.json";
in
lib.evalModules {
  modules = [
    (import ./stub-options.nix { inherit lib pkgs; })
    ({ config, lib, pkgs, ... }: {
      imports = [ ../../nix/module.nix ];
      agenixManager = {
        enable = true;
        secretsPath = "/secrets";
        manifestPath = manifestPath;
        keys.users = [ "ssh-ed25519 AAAA...u" ];
      };
    })
  ];
  specialArgs = { inherit pkgs; };
}
