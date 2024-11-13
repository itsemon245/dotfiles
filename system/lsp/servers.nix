{ pkgs, ... }:
{
  environment.systemPackages = with pkgs; [
    nodePackages.typescript-language-server
    tailwindcss-language-server
    nil
    gopls
    lua54Packages.lua-lsp
    psalm
    #new-server-here
  ];
}
