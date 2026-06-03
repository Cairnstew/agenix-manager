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
        keys.systems = [
          "ssh-ed25519 AAAA...s1"
          "ssh-ed25519 AAAA...s2"
          "ssh-ed25519 AAAA...s3"
        ];
        keys.users = [
          "ssh-ed25519 AAAA...u1"
          "ssh-ed25519 AAAA...u2"
        ];
        keys.other = [ "ssh-ed25519 AAAA...o1" ];
        identities = [ "/etc/ssh/ssh_host_ed25519_key" ];
        secrets = [
          { name = "host-key"; keys = "systems"; }
          { name = "user-key"; keys = "users"; }
          { name = "ci-key";   keys = "other"; }
          { name = "all-key";  keys = "all"; }
        ];
      };
    })
  ];
  specialArgs = { inherit pkgs; };
}
