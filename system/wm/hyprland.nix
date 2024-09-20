{inputs, pkgs,lib, ...}: {
  programs.hyprland = {
    enable = true;
    package = inputs.hyprland.packages.${pkgs.stdenv.hostPlatform.system}.hyprland;
    xwayland.enable = true;
  };
   services.logind.extraConfig = ''
    # don’t shutdown when power button is short-pressed
    HandlePowerKey=ignore
  '';
  environment.sessionVariables = {
    # If your cursor becomes invisible
    WLR_NO_HARDWARE_CURSORS = "1";
    # Hint electron apps to use wayland
    NIXOS_OZONE_WL = "1";
  };


  hardware = {
    opengl.enable = true;
  };

  environment.systemPackages = with pkgs; [
    #Bar
    (pkgs.waybar.overrideAttrs (oldAttrs: {
      mesonFlags = oldAttrs.mesonFlags ++ [ "-Dexperimental=true" ];
    }))

    #Notification Daemon
    mako
    dunst
    libnotify

    #wallpaper daemons
    swww
    hyprpaper

    #App Launcher
    rofi-wayland

    #Login Manager
    greetd.regreet
    wlogout
    swaylock

    #Compositor
    wlroots
    hyprland

    #Clipboard
    cliphist
    wl-clipboard

    #Screenshot
    maim
    xorg.xrandr
    wlr-randr
    xclip
    wl-clipboard-x11
    hyprshot

    #Music
    playerctl


  ];

  xdg.portal.enable = true;

  #Login Screen
  programs.regreet = {
    enable = true;
  };

  #Adjust dm and de and login
  services.xserver = {
    displayManager = {
      #Disable GDM
      gdm.enable = lib.mkForce false;
    };

    #Disable Gnome
    desktopManager.gnome = {
      enable = lib.mkForce false;
    };
  };
}
