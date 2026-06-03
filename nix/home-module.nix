{ config, lib, pkgs, ... }:

let
  cfg = config.homeManagerModules.agenix-manager;
in

{

  options.homeManagerModules.agenix-manager = {
    enable = lib.mkEnableOption "agenix-manager user packages";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.agenix-manager;
      defaultText = lib.literalExpression "pkgs.agenix-manager";
      description = "Package to add to the user session";
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages = [ cfg.package ];
  };

}
