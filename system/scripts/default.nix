{config, pkgs, ...}:
let
  t = import ./t.nix {inherit pkgs; };
  speedmeter = import ./speedmeter.nix {inherit pkgs; };
in {
    environment.systemPackages = [
        t 
        speedmeter
        pkgs.bat
    ];
}
