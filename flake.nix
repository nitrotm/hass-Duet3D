{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/25.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      ...
    }@inputs:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        inherit (nixpkgs) lib;

        pkgs = (import nixpkgs) {
          inherit system;
        };
      in
      rec {
        packages = {
        };

        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            gitFull
            nodejs_22
          ];
        };
      }
    );
}
