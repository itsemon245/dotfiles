{ pkgs, ... }:
{
  environment.systemPackages = with pkgs; [
    lua52Packages.lua-lsp
    gopls
    phpactor
    nil
    nodePackages.typescript-language-server
    tailwindcss-language-server
    nodePackages.volar
    php83Packages.psalm
    nodePackages.intelephense
    #new-server-here
  ];
}
