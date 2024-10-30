{
  description = "NixOs flakes configuration";

  inputs = {
    nixpkgs.url = "nixpkgs/24.05";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    hyprland.url = "git+https://github.com/hyprwm/Hyprland?submodules=1";
  };

  outputs = {self, nixpkgs, home-manager, ... } @ inputs:
    let
      #--- System Settings ---#
      system = {
        name = "x86_64-linux";
        hostname = "nixos";
        timezone = "Asia/Dhaka";
      };
      server = {
        memoryLimit = "200M";
        executionTime = "600"; #in seconds
      };

      #--- User Settings ---#
      user = {
        name = "emon";
        editor = "nvim";
        browser = "firefox";
      };

      lib = nixpkgs.lib;
      pkgs = nixpkgs.legacyPackages.${system.name};
  in {
    nixosConfigurations = {
      nixos = lib.nixosSystem {
        inherit system;
        modules = [
          ./system/configuration.nix
        ];
        specialArgs = {
          inherit system;
          inherit user;
          inherit server;
          inherit inputs;
        };
      };
    };
    homeConfigurations = {
      emon = home-manager.lib.homeManagerConfiguration {
        inherit pkgs;
        modules = [ ./user ];
        extraSpecialArgs = {
          inherit user;
        };
      };
    };
  };
}
