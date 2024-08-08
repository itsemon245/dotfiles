{
  description = "NixOs flakes configuration";

  inputs = {
    nixpkgs.url = "nixpkgs/24.05";
  };

  outputs = {self, nixpkgs, ... }:
    let
    lib = nixpkgs.lib;
  in {
    nixosConfigurations = {
      nixos = lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          ./configuration.nix
        ];
      };
    };
  };
}
