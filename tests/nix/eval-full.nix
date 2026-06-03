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
        secretsPath = "/var/secrets";
        keys.systems = [ "ssh-ed25519 AAAA...s" ];
        keys.users   = [ "ssh-ed25519 AAAA...u" ];
        keys.other   = [ "ssh-ed25519 AAAA...o" ];
        identities = [
          "/etc/ssh/ssh_host_ed25519_key"
          "/home/user/.ssh/id_ed25519"
        ];
        secrets = [
          { name = "sys-key"; keys = "systems"; owner = "root";   group = "root";   mode = "0400"; }
          { name = "user-token"; keys = "users";   owner = "alice"; group = "users";  mode = "0600"; }
          { name = "ci-secret";  keys = "other";   owner = "root";  group = "root";   mode = "0400"; }
          { name = "global-db";  keys = "all";     owner = "postgres"; group = "postgres"; mode = "0600"; }
        ];
      };
    })
  ];
  specialArgs = { inherit pkgs; };
}
