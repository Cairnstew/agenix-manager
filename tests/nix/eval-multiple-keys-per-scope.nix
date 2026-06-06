let
  pkgs = import <nixpkgs> {};
  lib = pkgs.lib;
  manifestPath = toString ./. + "/eval-multiple-keys-per-scope-manifest.json";
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
        keys.groups.systems = [
          "ssh-ed25519 AAAA...s1"
          "ssh-ed25519 AAAA...s2"
          "ssh-ed25519 AAAA...s3"
        ];
        keys.groups.users = [
          "ssh-ed25519 AAAA...u1"
          "ssh-ed25519 AAAA...u2"
        ];
        keys.groups.other = [ "ssh-ed25519 AAAA...o1" ];
        identities = [ "/etc/ssh/ssh_host_ed25519_key" ];
      };
    })
  ];
  specialArgs = { inherit pkgs; };
}
