{
  description = "Launcher application";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python313;
        ps = python.pkgs;

        pythonDeps = with ps; [
          brotli
          certifi
          charset-normalizer
          idna
          psutil
          py7zr
          pycryptodomex
          pyside6
          requests
          texttable
          urllib3
          typing-extensions
        ];

        launcher = ps.buildPythonApplication {
          pname = "launcher";
          version = "0.1.0";

          src = pkgs.lib.cleanSource ./base;

          format = "pyproject";
          build-system = [ ps.setuptools ];
          postPatch = ''
              python3 -c "
            import re, pathlib
            p = pathlib.Path('pyproject.toml')
            content = p.read_text()
            new = re.sub(r'dependencies = \[.*?\]', 'dependencies = []', content, flags=re.DOTALL)
            p.write_text(new)
            "
          '';
          propagatedBuildInputs = pythonDeps;

          meta = {
            description = "Launcher application";
            mainProgram = "launcher";
          };
        };

      in
      {
        packages = {
          inherit launcher;
          default = launcher;
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [ (python.withPackages (_: pythonDeps)) ];
        };

        apps.default = {
          type = "app";
          program = "${launcher}/bin/launcher";
        };
      }
    );
}
