{ pkgs, lib, pythonSet, system }:

let
  pkg = pythonSet."agenix-manager";
in
{

  build = pkg;

  venv = pythonSet.mkVirtualEnv "app-env" { agenix-manager = [ ]; };

}
