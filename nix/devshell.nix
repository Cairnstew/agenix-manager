{ pkgs, pythonSet, workspace, python }:

let
  virtualenv = pythonSet.mkVirtualEnv "agenix-manager-dev-env" workspace.deps.default;
in

{
  default = pkgs.mkShell {
    packages = [
      virtualenv
      pkgs.uv
      pkgs.age
    ];

    env = {
      UV_NO_SYNC = "1";
      UV_PYTHON = "${python.interpreter}";
      UV_PYTHON_DOWNLOADS = "never";
    };

    shellHook = ''
      unset PYTHONPATH
      export REPO_ROOT=$(git rev-parse --show-toplevel)
    '';
  };

  bootstrap = pkgs.mkShell {
    packages = [
      pkgs.python312
      pkgs.uv
    ];
  };
}
