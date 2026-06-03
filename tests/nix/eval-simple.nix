let
  pkgs = import <nixpkgs> {};
  lib = pkgs.lib;
  manifestPath = toString ./. + "/eval-simple-manifest.json";
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
        keys.systems = [ "ssh-ed25519 AAAA...test" ];
        identities = [ "/etc/ssh/ssh_host_ed25519_key" ];
      };
    })
  ];
  specialArgs = { inherit pkgs; };
}
