{
  description = "Development environment for the FlowForge ETL project";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
        };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            python312
            uv
            git
            ruff
            pyright
          ];

          shellHook = ''
            export UV_PYTHON_PREFERENCE=only-system
            export UV_PROJECT_ENVIRONMENT="$PWD/.venv"

            echo "FlowForge development environment"
            echo "Python: $(python --version)"
            echo "uv:     $(uv --version)"
            echo "Ruff:   $(ruff --version)"
            echo "Pyright: $(pyright --version)"

            # Git Configuration
            git config --global user.name "Alex Paquette"
            git config --global user.email "alexandre.d.paquette@gmail.com"
          '';
        };
      });
}