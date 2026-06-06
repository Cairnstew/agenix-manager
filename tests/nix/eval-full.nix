let
  pkgs = import <nixpkgs> {};
  lib = pkgs.lib;
  manifestPath = toString ./. + "/eval-full-manifest.json";
in
lib.evalModules {
  modules = [
    (import ./stub-options.nix { inherit lib pkgs; })
    ({ config, lib, pkgs, ... }: {
      imports = [ ../../nix/module.nix ];
      agenixManager = {
        enable = true;
        secretsPath = "/var/secrets";
        manifestPath = manifestPath;
        keys.groups.systems = [ "ssh-ed25519 AAAA...s" ];
        keys.groups.users   = [ "ssh-ed25519 AAAA...u" ];
        keys.groups.other   = [ "ssh-ed25519 AAAA...o" ];
        identities = [
          "/etc/ssh/ssh_host_ed25519_key"
          "/home/user/.ssh/id_ed25519"
        ];
      };
    })
  ];
  specialArgs = { inherit pkgs; };
}
