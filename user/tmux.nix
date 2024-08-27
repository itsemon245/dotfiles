{config, pkgs, ... }:
{
  programs.tmux = {
    enable = true;
    mouse = true;
    keyMode = "vi";
    disableConfirmationPrompt = true;
    shortcut = "space";
    baseIndex = 1;
    clock24 = false;
    shell = "/run/current-system/sw/bin/zsh";
    plugins = with pkgs; [
      {
        plugin = tmuxPlugins.sensible;
         extraConfig = ''
          #-----Overrides-----#
          #Set 24-bit colors for tmux sessions
          set -g default-terminal "tmux-256color"
          set -ag terminal-overrides ",xterm-256color:RGB"
          set -g default-terminal "xterm-kitty"
          set-option -sa terminal-overrides ",xterm*:Tc"
          set -s escape-time 0
          # Increase scrollback buffer size
          set -g history-limit 10000

          #----Bindings----#
          #Open panes in current working directory
          bind '-' split-window -v -c "#{pane_current_path}"
          bind '\' split-window -h -c "#{pane_current_path}"

          # Smart pane switching with awareness of vim splits
          is_vim='echo "#{pane_current_command}" | grep -iqE "(^|\/)g?(view|n?vim?)(diff)?$"'
          bind -n C-h if-shell "$is_vim" "send-keys C-h" "select-pane -L"
          bind -n C-j if-shell "$is_vim" "send-keys C-j" "select-pane -D"
          bind -n C-k if-shell "$is_vim" "send-keys C-k" "select-pane -U"
          bind -n C-l if-shell "$is_vim" "send-keys C-l" "select-pane -R"

          #Set Binding To start new sessions from office dirs
          bind-key -r F new-window t
          bind-key -r D run-shell "t ~/dotfiles"

          #Switch between last window by holding ctrl and pressing space twice
          bind Space last-window

          #Start windows and panes at 1, not 0
          set-window-option -g pane-base-index 1
          set-option -g renumber-windows on

          # Status line customisation
          set-option -g status-position top
          set-option -g status-left-length 100
          set-option -g status-right-length 100
          set-option -g status-left " #{session_name}  "
          set-option -g status-right "#{pane_title} "
          set-option -g status-style "fg=#7C7D83 bg=#242631"
          set-option -g window-status-format "#{window_index}:#{pane_current_command}#{window_flags} "
          set-option -g window-status-current-format "#{window_index}:#{pane_current_command}#{window_flags} "
          set-option -g window-status-current-style "fg=#E9E9EA"
          set-option -g window-status-activity-style none

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
