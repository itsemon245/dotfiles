{config, lib, pkgs, ...}:
{

  environment.systemPackages = with pkgs; [
    node
    php81
  ];
}
