{
  description = "NixOs flakes configuration";

  inputs = {
    nixpkgs.url = "github:NixOs/nixpkgs/nixos-unstable";
  };

  outputs = {self, nixpkgs, ... }:
    let
    lib = nixpkgs.lib;
  in {
    nixosConfigurations = {
      nixos = lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          "./configuration.nix"
        ];
      };
    };
  };
}
