{ config, pkgs, ... }:

{

  home.username = "emon";
  home.homeDirectory = "/home/emon";
  home.stateVersion = "24.05"; # Please read the comment before changing.

  # Let Home Manager install and manage itself.
  programs.home-manager.enable = true;

  # The home.packages option allows you to install Nix packages into your
  # environment.
  home.packages = with pkgs; [
    hello
    thefuck
  ];

  # Home Manager is pretty good at managing dotfiles. The primary way to manage
  # plain files is through 'home.file'.
  home.file = {
    ".zshrc".text = ''
    source ~/dotfiles/zsh/.zshrc.source
    '';
    # # Building this configuration will create a copy of 'dotfiles/screenrc' in
    # # the Nix store. Activating the configuration will then make '~/.screenrc' a
    # # symlink to the Nix store copy.
    # ".screenrc".source = dotfiles/screenrc;

    # # You can also set the file content immediately.
    # ".gradle/gradle.properties".text = ''
    #   org.gradle.console=verbose
    #   org.gradle.daemon.idletimeout=3600000
    # '';
  };
  home.sessionVariables = {
    EDITOR = "vim";
  };

  #ZSH Setup

  programs.zsh = {
    enable = true;
    enableCompletion = true;
    autosuggestion.enable = true;
    syntaxHighlighting.enable = true;

    shellAliases = {
      ll = "ls -l";
      update = "sudo nixos-rebuild switch --flake ~/dotfiles";
      "update-home" = "home-manager switch --flake ~/dotfiles";
    };
    history = {
      size = 10000;
      path = "${config.xdg.dataHome}/zsh/history";
    };
    oh-my-zsh = {
      enable = true;
      plugins = [ "git" "thefuck" ];
      theme = "robbyrussell";
    };

  };

  #TMUX Setup
  programs.tmux = {
    enable = true;
    mouse = true;
    keyMode = "vi";
    disableConfirmationPrompt = true;
    shortcut = "space";
    baseIndex = 1;
    clock24 = false;
    shell = "$SHELL";
    plugins = with pkgs; [
      {
        plugin = tmuxPlugins.sensible;
         extraConfig = ''
          #-----Overrides-----#
          #Set 24-bit colors for tmux sessions
          set -g default-terminal "tmux-256color"
          set -ag terminal-overrides ",xterm-256color:RGB"
          set -g default-terminal "tmux"
          set-option -sa terminal-overrides ",xterm*:Tc"

          #---Bindings----#
          #Open panes in current working directory
          bind '-' split-window -v -c "#{pane_current_path}"
          bind '\' split-window -h -c "#{pane_current_path}"

          #Start windows and panes at 1, not 0
          set-window-option -g pane-base-index 1
          set-option -g renumber-windows on

          #Set status position to top
          set-option -g status-position top

          #Shift Alt Vim keys to switch windows
          bind -n M-H previous-window
          bind -n M-L next-window
        '';
      }
      tmuxPlugins.vim-tmux-navigator
      tmuxPlugins.yank
      tmuxPlugins.prefix-highlight
      tmuxPlugins.open
      tmuxPlugins.net-speed
      tmuxPlugins.better-mouse-mode
      tmuxPlugins.vim-tmux-navigator
      tmuxPlugins.catppuccin
      {
      
        plugin = tmuxPlugins.copycat;
        extraConfig = ''
          bind-key -T copy-mode-vi v send-keys -X begin-selection
          bind-key -T copy-mode-vi C-v send-keys -X rectangle-toggle
          bind-key -T copy-mode-vi y send-keys -X copy-selection-and-cancel
        '';
      }
      {
        plugin = tmuxPlugins.resurrect;
        extraConfig = "set -g @resurrect-strategy-nvim 'session'";
      }
      {
        plugin = tmuxPlugins.continuum;
        extraConfig = ''
          set -g @continuum-restore 'on'
          set -g @continuum-save-interval '60' # minutes
          set -g status-right 'Continuum status: #{continuum_status}'
        '';
      }
      {
        plugin = tmuxPlugins.dracula;
        extraConfig = ''
          set -g @dracula-show-powerline true
          set -g @dracula-fixed-location "NYC"
          set -g @dracula-plugins "weather"
          set -g @dracula-show-flags true
          set -g @dracula-show-left-icon session
        '';
      }
    ];
   
  };
}
