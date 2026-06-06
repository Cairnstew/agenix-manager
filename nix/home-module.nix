{ config, lib, pkgs, agenixPackage ? null, ... }:

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

    agenixPackage = lib.mkOption {
      type = lib.types.nullOr lib.types.package;
      default = agenixPackage;
      defaultText = lib.literalMD "The agenix package from the flake input";
      description = ''
        The agenix package providing the ``agenix`` binary.  When set (not
        ``null``), the binary is added to ``home.packages`` and
        ``AGENIX_BIN`` is set in ``home.sessionVariables`` so that the
        CLI can discover it without a ``$PATH`` lookup.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages = [ cfg.package pkgs.age ]
      ++ lib.optional (cfg.agenixPackage != null) cfg.agenixPackage;

    home.sessionVariables = lib.mkIf (cfg.agenixPackage != null) {
      AGENIX_BIN = "${cfg.agenixPackage}/bin/agenix";
    };
  };

}
