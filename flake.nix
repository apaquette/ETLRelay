{
  description = "Development environment for the ETLRelay ETL project";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

    fix-python.url = "github:GuillaumeDesforges/fix-python";
  };

  outputs =
    { nixpkgs, fix-python, ... }:
    let
      systems = nixpkgs.lib.systems.flakeExposed;
    in
    {
      devShells = nixpkgs.lib.genAttrs systems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.python312
              pkgs.uv
              pkgs.git
              pkgs.ruff
              pkgs.pyright
              fix-python.packages.${system}.default
            ];

            env = {
              UV_PYTHON_PREFERENCE = "only-system";
              UV_PYTHON_DOWNLOADS = "never";
            };

            shellHook = ''
              if [ ! -x "$PWD/.venv/bin/python" ]; then
                python -m venv "$PWD/.venv" --copies
              fi

              export VIRTUAL_ENV="$PWD/.venv"
              export PATH="$VIRTUAL_ENV/bin:$PATH"

              echo "ETLRelay development environment"
              echo "Python: $(python --version)"
              echo "uv:     $(uv --version)"
              echo "Ruff:   $(ruff --version)"
              echo "Pyright: $(pyright --version)"

              # Git Configuration
              git config --global user.name "Alex Paquette"
              git config --global user.email "alexandre.d.paquette@gmail.com"

              exec fish
            '';
          };
        }
      );
    };
}