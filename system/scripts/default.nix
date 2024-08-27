{config, pkgs, ...}:
let
  t = import ./t.nix {inherit pkgs; };
  netspeed = import ./netspeed.nix {inherit pkgs; };
  usages = import ./usages.nix {inherit pkgs; };
in {
    environment.systemPackages = [
        t 
        netspeed
        usages
        pkgs.bat
    ];
}
