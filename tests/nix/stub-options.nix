{ lib, pkgs, ... }: {
  options = {
    age.secrets = lib.mkOption { type = lib.types.attrsOf lib.types.raw; default = {}; };
    age.identityPaths = lib.mkOption { type = lib.types.listOf lib.types.str; default = []; };
    environment.systemPackages = lib.mkOption { type = lib.types.listOf lib.types.package; default = []; };
    system.activationScripts = lib.mkOption {
      type = lib.types.attrsOf (lib.types.submodule {
        options = {
          text = lib.mkOption { type = lib.types.lines; };
          deps = lib.mkOption { type = lib.types.listOf lib.types.str; default = []; };
        };
      });
      default = {};
    };
  };
}
