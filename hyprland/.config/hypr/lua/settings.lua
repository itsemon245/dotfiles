---@type Dotfiles.Settings
return {
  apps = {
    terminal = "kitty",
    browser = "google-chrome-stable --enable-features=UseOzonePlatform,WaylandLinuxDrmSyncobj --ozone-platform=wayland",
    file_manager = "nemo",
    menu = "~/.config/rofi/launchers/type-3/launcher.sh",
  },
  commands = {
    startup = "~/.local/bin/hypr-startup",
    clipboard_text_watcher = "wl-paste --type text --watch cliphist store",
    clipboard_image_watcher = "wl-paste --type image --watch cliphist store",
    clipboard_menu = "rofi -modi clipboard:~/.config/rofi/scripts/clipboard -show clipboard -show-icons -theme ~/.config/rofi/launchers/type-4/style-6-clipboard.rasi",
    wallpaper_menu = "~/.local/bin/wally",
    wallpaper_upscale_menu = "~/.local/bin/wally -u",
    readable_window = "~/.local/bin/readable-window",
    rofi_vpn = "~/.local/bin/rofi-vpn",
    rofi_monitor = "~/.local/bin/rofi-monitor",
    refresh_bar = "~/.local/bin/barr",
    toggle_bar = "~/.local/bin/barr --toggle",
    regenerate_theme = "wallust run ~/Wallpapers/default.png",
  },
  screenshot_directory = "~/Pictures/Screenshots",
  main_mod = "SUPER",
  workspace_count = 10,
  special_workspace = "magic",
}
