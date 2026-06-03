{
  description = "NixOS module + TUI CLI for declarative agenix secret management";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    agenix = {
      url = "github:ryantm/agenix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      agenix,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
      ...
    }:
    let
      inherit (nixpkgs) lib;
      forAllSystems = lib.genAttrs lib.systems.flakeExposed;

      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

      overlay = workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      };

      pythonSets = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python312;

          baseSet = pkgs.callPackage pyproject-nix.build.packages {
            inherit python;
          };

          pythonSet = baseSet.overrideScope (
            lib.composeManyExtensions [
              pyproject-build-systems.overlays.wheel
              overlay
            ]
          );
        in
        {
          inherit pythonSet python pkgs;
        }
      );
    in
    {
      packages = forAllSystems (
        system:
        let
          p = pythonSets.${system};
          vmTests_ = p.pkgs.callPackage ./nix/vm-tests.nix {
            inherit agenix;
            agenixManagerModule = ./nix/module.nix;
          };
        in
        {
          default = p.pkgs.callPackage ./nix/default.nix {
            inherit (p) pythonSet pkgs;
            inherit workspace pyproject-nix;
          };

          vmTest = vmTests_.basic;
        }
      );

      devShells = forAllSystems (
        system:
        let p = pythonSets.${system}; in
        p.pkgs.callPackage ./nix/devshell.nix {
          inherit (p) pythonSet python pkgs;
          inherit workspace;
        }
      );

      overlays.default = final: prev: {
        agenix-manager = pythonSets.${prev.stdenv.hostPlatform.system}.pythonSet."agenix-manager";
      };

      nixosModules.default = import ./nix/module.nix;

      homeManagerModules.default = import ./nix/home-module.nix;

      checks = forAllSystems (
        system:
        let p = pythonSets.${system}; in
        p.pkgs.callPackage ./nix/checks.nix {
          inherit lib system;
          pythonSet = p.pythonSet;
        }
      );

      vmTests = forAllSystems (system:
        let p = pythonSets.${system}; in
        p.pkgs.callPackage ./nix/vm-tests.nix {
          inherit agenix;
          agenixManagerModule = ./nix/module.nix;
        }
      );
    };
}
