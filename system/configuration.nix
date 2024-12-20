# Edit this configuration file to define what should be installed on your system.  Help is available in the configuration.nix(5) man page and in the NixOS manual (accessible by
# running ‘nixos-help’).

{ config,lib, pkgs, system, user, ... }:

{
  imports =
    [ # Include the results of the hardware scan.
      ./hardware
      ./packages.nix
      ./lsp/servers.nix
      ./scripts/default.nix
      ./dev
      ./nginx/default.nix
      ./gaming/default.nix
      ./wm/hyprland.nix
    ];

  # Bootloader.
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;
  boot.kernelPackages = pkgs.linuxPackages_latest;

  networking.hostName = system.hostname; # Define your hostname.
  # networking.wireless.enable = true;  # Enables wireless support via wpa_supplicant.

  #ENABLE BLUEMAN
  # Make all bluetooth options in single object
  hardware.bluetooth = {
    enable = true;
    # Enables Bluetooth on startup
    powerOnBoot = true;
  };
  services.blueman.enable = true;

  #Daemons to detect portable devices
  services.udisks2.enable = true;

  # Configure network proxy if necessary
  # networking.proxy.default = "http://user:password@proxy:port/";
  # networking.proxy.noProxy = "127.0.0.1,localhost,internal.domain";

  #Enable numlock on boot
  # systemd.services.numLockOnTty = {
  #   wantedBy = [ "multi-user.target" ];
  #   after = [ "getty.target" ];
  #   path = [ pkgs.kbd ];  # Ensure `setleds` is available in the PATH
  #   serviceConfig = {
  #     ExecStart = lib.mkForce "${pkgs.runtimeShell}/bin/sh -c '' for tty in /dev/tty{1..6}; do ${pkgs.kbd}/bin/setleds -D +num < \"$tty\"; done ''";
  #   };
  # };
  # Enable networking
  networking.networkmanager.enable = true;

  # Enable Experimental Features
  nix.settings.experimental-features = ["nix-command" "flakes"];
  # Set your time zone
  time.timeZone = system.timezone;

  # Select internationalisation properties.
  i18n.defaultLocale = "en_US.UTF-8";

  i18n.extraLocaleSettings = {
    LC_ADDRESS = "bn_BD";
    LC_IDENTIFICATION = "bn_BD";
    LC_MEASUREMENT = "bn_BD";
    LC_MONETARY = "bn_BD";
    LC_NAME = "bn_BD";
    LC_NUMERIC = "bn_BD";
    LC_PAPER = "bn_BD";
    LC_TELEPHONE = "bn_BD";
    LC_TIME = "bn_BD";
  };

  services.incron = {
    enable = true;
  };


  # Configure keymap in X11
  services.xserver = {
    enable = true;
    xkb = {
      layout = "us";
      variant = "";
    };
    displayManager.gdm = {
      enable = true;
    };
    desktopManager.gnome = {
      enable = true;
    };
  };

  # Enable CUPS to print documents.
  services.printing.enable = true;

  # Enable sound with pipewire.
  hardware.pulseaudio.enable = false;
  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
    # If you want to use JACK applications, uncomment this
    jack.enable = true;

    # use the example session manager (no others are packaged yet so this is enabled by default,
    # no need to redefine it in your config for now)
    #media-session.enable = true;
  };

  # Enable touchpad support (enabled default in most desktopManager).
  # services.xserver.libinput.enable = true;

  # Define a user account. Don't forget to set a password with ‘passwd’.
  users.users.${user.name} = {
    shell = pkgs.zsh;
    isNormalUser = true;
    description = "Mojahidul Islam";
    extraGroups = [ "networkmanager" "wheel" ];
  };

  # Install firefox.
  programs.firefox.enable = true;
  programs.zsh.enable = true;

  # Allow unfree packages
  nixpkgs.config.allowUnfree = true;
  # Fonts
  fonts = {
    enableDefaultPackages = true;
    packages = with pkgs; [
      (nerdfonts.override { fonts = [ "FiraCode" "DroidSansMono" "CascadiaCode"]; })
      font-awesome
      noto-fonts
      noto-fonts-color-emoji
      lohit-fonts.bengali
    ];
    fontconfig = {
      defaultFonts = {
        monospace = [ "CascadiaCode" ];
      };
    };
  };


  # Some programs need SUID wrappers, can be configured further or are
  # started in user sessions.
  # programs.mtr.enable = true;
  # programs.gnupg.agent = {
  #   enable = true;
  #   enableSSHSupport = true;
  # };

  # List services that you want to enable:

  # Enable the OpenSSH daemon.
  services.openssh.enable = true;

  #Enables cron jobs
  services.cron = {
    enable = true;
    systemCronJobs = [
      # Run nixos-garbage-collect every every 3days
      "*/3 * * * * root nix-collect-garbage --delete-older-than 3d"
    ];
  };

  # Open ports in the firewall.
  networking.firewall.allowedUDPPorts = [{ from = 4000; to = 4007; } { from = 8000; to = 8010; }];
  networking.firewall.allowedTCPPorts = [{ from = 80; to = 100; }];
  # Or disable the firewall altogether.
  networking.firewall.enable = false;

  # This value determines the NixOS release from which the default
  # settings for stateful data, like file locations and database versions
  # on your system were taken. It‘s perfectly fine and recommended to leave
  # this value at the release version of the first install of this system.
  # Before changing this value read the documentation for this option
  # (e.g. man configuration.nix or on https://nixos.org/nixos/options.html).
  system.stateVersion = "24.05"; # Did you read the comment?
}
