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

        pythonDeps = [
          ps.brotli
          ps.certifi
          ps.charset-normalizer
          ps.idna
          ps.psutil
          ps.py7zr
          ps.pycryptodomex
          ps.pyside6
          ps.requests
          ps.texttable
          ps.urllib3
        ];

        launcher = ps.buildPythonApplication {
          pname = "launcher";
          version = "0.1.0";

          src = pkgs.lib.cleanSource ./base;

          format = "pyproject";
          build-system = [ ps.setuptools ];

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
