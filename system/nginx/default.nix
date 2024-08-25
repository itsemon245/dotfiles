{ config,pkgs, lib, ...}: 
{
  environment.systemPackages = with pkgs; [
  ];
  imports = [
    ./vhosts/phpmyadmin.nix
  ];
  services.nginx.enable = true;

  services.mysql = {
    enable = true;
    package = pkgs.mariadb;
  };

  networking.extraHosts =
    ''
    127.0.0.1 localhost
    '';

}
