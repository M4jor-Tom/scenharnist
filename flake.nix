{
  description = "scenharnist — prompt -> animated glTF + video via any LLM";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.waifus = { url = "github:M4jor-Tom/waifus.gltf"; flake = false; };
  outputs = { self, nixpkgs, flake-utils, waifus }:
    flake-utils.lib.eachSystem [
      "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"
    ] (system:
      let
        pkgs = import nixpkgs { inherit system; config.allowUnfree = true; };
        # ponytail: python311Packages.litellm is broken in this nixpkgs pin
        # (pulls sphinx-9.1.0, disabled for python3.11) — install litellm via
        # `pip install -e .` instead; drop this comment once nixpkgs fixes it.
        py = pkgs.python311.withPackages (p: [ p.pytest ]);
        deps = [ py pkgs.blender ];
      in {
        devShells.default = pkgs.mkShell { packages = deps; };
        apps.default = {
          type = "app";
          program = toString (pkgs.writeShellScript "scenharnist" ''
            export PATH=${pkgs.lib.makeBinPath deps}:$PATH
            cd ${self}
            exec ${py}/bin/python -m scenharnist.cli "$@"
          '');
        };
        apps.test = {
          type = "app";
          program = toString (pkgs.writeShellScript "scenharnist-test" ''
            export PATH=${pkgs.lib.makeBinPath deps}:$PATH
            cd ${self} && exec ${py}/bin/python -m pytest -q
          '');
        };
        apps.test-prompting = {
          type = "app";
          program = toString (pkgs.writeShellScript "scenharnist-test-prompting" ''
            export PATH=${pkgs.lib.makeBinPath deps}:$PATH
            export SCENHARNIST_GLTF_ROOT=${waifus}
            cd ${self}
            exec ${py}/bin/python -m pytest -m prompting "$@"
          '');
        };
      });
}
