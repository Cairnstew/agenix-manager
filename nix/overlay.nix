{ pkgs, workspace, pyproject-build-systems, pyproject-nix, pythonSet }:

final: prev: {

  agenix-manager = pythonSet."agenix-manager";

  agenix-manager-env = pythonSet.mkVirtualEnv "app-env" workspace.deps.default;

}
