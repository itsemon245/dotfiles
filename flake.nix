{
  description = "NixOs flakes configuration";

  inputs = {
    nixpkgs.url = "nixpkgs/24.05";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = {self, nixpkgs, home-manager, ... }:
    let
    system = "x86_64-linux";
    lib = nixpkgs.lib;
    pkgs = nixpkgs.legacyPackages.${system};
  in {
    nixosConfigurations = {
      nixos = lib.nixosSystem {
        inherit system;
        modules = [
          ./configuration.nix
        ];
      };
    };
    homeConfigurations = {
      emon = home-manager.lib.homeManagerConfiguration {
        inherit pkgs;

        modules = [ ./users/emon.nix ];
      };
    };
  };
}
