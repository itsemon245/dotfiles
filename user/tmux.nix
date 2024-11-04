{config, pkgs, ... }:
{
  programs.tmux = {
    enable = true;
    mouse = true;
    keyMode = "vi";
    disableConfirmationPrompt = true;
    sensibleOnTop = false;
    shortcut = "space";
    baseIndex = 1;
    clock24 = false;
    shell = "${pkgs.zsh}/bin/zsh";
    terminal = "xterm-kitty";
    plugins = with pkgs; [
      {
        plugin = tmuxPlugins.sensible;
        extraConfig = ''
          set -ag terminal-overrides ",xterm-256color:RGB"
          set-option -sa terminal-overrides ",xterm*:Tc"
          set -s escape-time 0
          set -g history-limit 10000

          bind '-' split-window -v -c "#{pane_current_path}"
          bind '\' split-window -h -c "#{pane_current_path}"
          bind C-k send-keys "clear"\; send-keys "Enter"
          is_vim='echo "#{pane_current_command}" | grep -iqE "(^|\/)g?(view|n?vim?)(diff)?$"'
          bind -n C-h if-shell "$is_vim" "send-keys C-h" "select-pane -L"
          bind -n C-j if-shell "$is_vim" "send-keys C-j" "select-pane -D"
          #bind -n C-k if-shell "$is_vim" "send-keys C-k" "select-pane -U"
          bind -n C-l if-shell "$is_vim" "send-keys C-l" "select-pane -R"

          bind-key -r F new-window t
          bind-key -r D run-shell "t ~/dotfiles"

          bind Space last-window

          set-window-option -g pane-base-index 1
          set-option -g renumber-windows on

          set-option -g status-position top
          set-option -g status-left-length 100
          set-option -g status-right-length 100
          set-option -g status-left " #{session_name}  "
          set-option -g status-right "#{user}@#{host}"
          set-option -g status-style "fg=#7C7D83 bg=#242631"
          # Center the status bar
          set -g status-justify centre
          set-option -g window-status-format " #{window_index}:#{window_name}#{window_flags} "
          set-option -g window-status-current-format " #{window_index}:#{window_name}#{window_flags} "
          set-option -g window-status-current-style "fg=#CA9EE6"
          set-option -g window-status-activity-style none

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
          # set -g status-right 'Continuum status: #{continuum_status}'
        '';
      }
    ];
  };
}
