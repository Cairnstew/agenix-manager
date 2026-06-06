{ pkgs, agenix, agenixManagerModule }:

let
  common = import ../tests/nixos/common.nix { inherit pkgs; };

  scenarioFiles = {
    basic = import ../tests/nixos/scenarios/basic.nix;
    multi-secret = import ../tests/nixos/scenarios/multi-secret.nix;
    custom-perms = import ../tests/nixos/scenarios/custom-perms.nix;
    user-keys = import ../tests/nixos/scenarios/user-keys.nix;
  };

  runOne = name: scenarioFn:
    let
      scenario = scenarioFn {
        inherit pkgs agenix agenixManagerModule common;
      };
    in
    pkgs.testers.runNixOSTest {
      name = "agenix-manager-${scenario.name}";
      nodes.machine = { ... }: {
        imports = [ scenario.nodeConfig ];
        _module.args.agenixPackage = agenix.packages.${pkgs.stdenv.hostPlatform.system}.default;
      };
      testScript = scenario.testScript;
    };
in
builtins.mapAttrs runOne scenarioFiles
