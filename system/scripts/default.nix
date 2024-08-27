{config, pkgs, ...}:
let
  t = import ./t.nix {inherit pkgs; };
  speedmeter = import ./speedmeter.nix {inherit pkgs; };
  usages = import ./usages.nix {inherit pkgs; };
in {
    environment.systemPackages = [
        t 
        speedmeter
        usages
        pkgs.bat
    ];
}
