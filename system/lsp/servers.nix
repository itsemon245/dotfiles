{ pkgs, ... }:
{
  environment.systemPackages = with pkgs; [
    lua52Packages.lua-lsp
    gopls
    phpactor
    nil
    tailwindcss-language-server
    nodePackages.volar
    php83Packages.psalm
    nodePackages.intelephense
    nodePackages.typescript-language-server
    #new-server-here
  ];
}
