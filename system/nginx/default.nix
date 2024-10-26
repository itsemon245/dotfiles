{ config,pkgs, lib, ...}:
{
  imports = [
    ./vhosts/phpmyadmin.nix
  ];
  services.nginx.enable = true;

  services.mysql = {
    enable = true;
    package = pkgs.mysql;
  };

  networking.extraHosts =
    ''
    127.0.0.1 localhost
    '';

}
