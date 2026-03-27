{
  description = "Launcher application";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python313;
        ps = python.pkgs;

        # ── Packages not yet in nixpkgs ──────────────────────────────────
        inflate64 = ps.buildPythonPackage rec {
          pname   = "inflate64";
          version = "1.0.4";
          format  = "pyproject";
          src = ps.fetchPypi {
            inherit pname version;
            sha256 = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
          };
          build-system = [ ps.setuptools ];
        };

        multivolumefile = ps.buildPythonPackage rec {
          pname   = "multivolumefile";
          version = "0.2.3";
          format  = "pyproject";
          src = ps.fetchPypi {
            inherit pname version;
            sha256 = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
          };
          build-system = [ ps.setuptools ];
        };

        pybcj = ps.buildPythonPackage rec {
          pname   = "pybcj";
          version = "1.0.7";
          format  = "pyproject";
          src = ps.fetchPypi {
            inherit pname version;
            sha256 = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
          };
          build-system = [ ps.setuptools ];
        };

        pyppmd = ps.buildPythonPackage rec {
          pname   = "pyppmd";
          version = "1.3.1";
          format  = "pyproject";
          src = ps.fetchPypi {
            inherit pname version;
            sha256 = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
          };
          build-system = [ ps.setuptools ];
        };

        # ── Dependency list ──────────────────────────────────────────────
        pythonDeps = [
          ps.brotli
          ps.certifi
          ps.charset-normalizer
          ps.idna
          inflate64
          multivolumefile
          ps.psutil
          ps.py7zr
          pybcj
          ps.pycryptodomex
          pyppmd
          ps.pyside6
          ps.requests
          ps.texttable
          ps.urllib3
        ];

        # ── Main package ─────────────────────────────────────────────────
        launcher = ps.buildPythonApplication {
          pname   = "launcher";
          version = "0.1.0";

          # Point src at the repo root; adjust if your source lives elsewhere.
          src = ./.;

          # The installable Python package lives under ./base/
          sourceRoot = "source/base";

          format = "pyproject";           # or "setuptools" if you have setup.py
          build-system = [ ps.setuptools ];

          propagatedBuildInputs = pythonDeps;

          # Override the entry point so `launcher` on PATH runs __init__.py
          postInstall = ''
            makeWrapper ${python}/bin/python $out/bin/launcher \
              --add-flags "$out/${python.sitePackages}/launcher/__init__.py" \
              --prefix PYTHONPATH : "$out/${python.sitePackages}"
          '';

          meta = {
            description = "Launcher application";
            mainProgram  = "launcher";
          };
        };

      in {
        # ── Outputs ──────────────────────────────────────────────────────
        packages = {
          inherit launcher;
          default = launcher;
        };

        # Drop into a dev shell that mirrors the venv the .cmd file builds
        devShells.default = pkgs.mkShell {
          buildInputs = [ (python.withPackages (_: pythonDeps)) ];
        };

        apps.default = {
          type    = "app";
          program = "${launcher}/bin/launcher";
        };
      }
    );
}
