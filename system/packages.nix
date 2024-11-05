{pkgs, ...}:
let
  unstable = import
    (builtins.fetchTarball {
      url = "https://github.com/nixos/nixpkgs/tarball/41dea55321e5a999b17033296ac05fe8a8b5a257";
      sha256 = "sha256:0wd5h8na7dlqdyvcvqlkgw84sj956yiq39jkljm0z7v7sg6dgwjs";
    }) { inherit (pkgs) system; config.allowUnfree = true;};
in
{
  environment.systemPackages = with pkgs; [
    vim
    unstable.neovim
    unstable.vscode
    lua
    luajitPackages.luarocks
    lua-language-server
    stylua
    cargo
    unzip
    zsh
    git
    gcc
    ripgrep
    tmux
    kitty
    pavucontrol
    pulseaudio
    gnome.nautilus
    cinnamon.nemo-with-extensions
    gparted
    vlc
    zoom-us
    incron
    distrobox
    podman
    postman
    google-chrome
    # Download Managers
    motrix
  ];
}
