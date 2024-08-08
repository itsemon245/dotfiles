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
    homeConfigurations{
      emon = home-manager.lib.homeManagerConfiguration {
        inherit pkgs;

        home.username = "emon";
        home.homeDirectory = "/home/emon";
        home.stateVersion = "23.11"; # Please read the comment before changing.

        # Let Home Manager install and manage itself.
        programs.home-manager.enable = true;

        modules = [ ./users/emon.nix ];
      };
    }
  };
}
