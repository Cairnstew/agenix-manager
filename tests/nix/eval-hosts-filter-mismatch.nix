let
  pkgs = import <nixpkgs> {};
  lib = pkgs.lib;
  manifestPath = toString ./. + "/manifest-hosts.json";
in
lib.evalModules {
  modules = [
    (import ./stub-options.nix { inherit lib pkgs; })
    ({ config, lib, pkgs, ... }: {
      options.networking.hostName = lib.mkOption {
        type = lib.types.str;
        default = "other-host";
      };
    })
    ({ config, lib, pkgs, ... }: {
      imports = [ ../../nix/module.nix ];
      agenixManager = {
        enable = true;
        secretsPath = "/secrets";
        manifestPath = manifestPath;
        keys.groups.systems = [ "ssh-ed25519 AAAA...testkey" ];
        keys.groups.users   = [ "ssh-ed25519 AAAA...userkey" ];
        identities = [ "/etc/ssh/ssh_host_ed25519_key" ];
      };
    })
  ];
  specialArgs = { inherit pkgs; };
}
