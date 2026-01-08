# Dotfiles Organization Guide

This document provides a comprehensive guide to understanding and working with this dotfiles repository structure, management system, and the unified theming architecture.

## Overview

This dotfiles repository uses **GNU Stow** for symlink-based configuration management. Each top-level directory represents a stow package that gets symlinked into the user's home directory (`~`).

- **Single source of truth** - All configs in one git repository
- **Unified Theming** - Wallust & Wally drive system-wide colors (GTK, Qt, Waybar, Hyprland, etc.)
- **Modular organization** - Each application gets its own package directory
- **Cross-machine setup** - Clone and stow on any machine

## Repository Structure

### Core Files

- **`install.sh`** - Main installation script.
- **`stow.sh`** - Stows all directories not listed in `.installignore`.
- **`colors.sh`** - Defines color variables for scripts.
- **`.stow-local-ignore`** - Patterns to exclude (`.git`, `*.log`, `README.md`).
- **`.installignore`** - Directories to exclude from stowing (`user`, `system`).

### Theming Architecture (New)

The repository implements a **Unified Source of Truth** for theming. Colors are derived from the wallpaper and injected into all applications automatically.

#### 1. The Controller: `wally`
Located in: `customization/bin/wally`
A robust CLI utility that orchestrates the entire visual stack.

*   **Capabilities:**
    *   **Wallpaper Picker:** Rofi-based GUI to select wallpapers from `~/Wallpapers`.
    *   **AI Upscaling:** Uses `realesrgan-ncnn-vulkan` (Anime model) to upscale low-res images.
    *   **Optimization:** Automatically downscales massive AI outputs to monitor resolution (e.g., 2560px) to prevent bloat.
    *   **Smart Caching:** Caches upscaled images in `~/.cache/wally`.
    *   **Theme Generation:** Triggers `wallust` to generate color schemes.
    *   **Live Reload:** Hot-reloads Waybar, Dunst, Hyprland, Kitty, and Qt apps.

*   **Usage:**
    ```bash
    wally               # Open Rofi Menu
    wally -u            # Open Menu + Upscale selected
    wally set img.jpg   # Set specific image
    wally --no-upscale  # Force original image
    ```

#### 2. The Engine: `wallust`
Located in: `wallust/` (Stow package)
Configured in: `~/.config/wallust/wallust.toml` (v3 syntax).

*   **Backend:** `wal` (Dark16 palette)
*   **Templates:**
    *   `hyprland-colors.conf` → `~/.config/hypr/colors.conf`
    *   `waybar-colors.css` → `~/.config/waybar/colors.css`
    *   `dunstrc` → `~/.config/dunst/dunstrc`
    *   `rofi-colors.rasi` → `~/.config/rofi/colors.rasi`
    *   `kitty-colors.conf` → `~/.config/kitty/colors.conf`
    *   `qt-colors.conf` → `~/.config/qt5ct/colors/wally.conf`
    *   `gtk.css` → `~/.config/gtk-4.0/gtk.css` & `gtk-3.0/gtk.css`

### Stow Packages (Top-Level Directories)

Each directory in the root is a stow package that gets symlinked to `~`:

#### Window Management & Desktop
- **`hyprland/`** - Hyprland window manager config.
  - `hyprland.conf` - Main config.
  - `keybinds.conf` - Key definitions (includes `Super+W` for wally).
  - `colors.conf` - **Auto-generated** color variables.
  - `windowrules.conf` - Application rules.

- **`waybar/`** - Status bar.
  - `config.jsonc` - Bar layout.
  - `style.css` - Stylesheet (Imports `colors.css`).
  - `colors.css` - **Auto-generated** color definitions.

- **`dunst/`** - Notification daemon.
  - `dunstrc` - Notification daemon config (templated via Wallust).

- **`rofi/`** - App launcher.
  - `config.rasi` - Main config.
  - `colors.rasi` - **Auto-generated** colors.

#### Application Configurations
- **`wallust/`** - Theming engine configuration.
  - `.config/wallust/wallust.toml` - Template mappings.
  - `.config/wallust/templates/` - Source templates for all apps.

- **`kitty/`** - Terminal config.
  - `kitty.conf` - Includes `colors.conf`.
  - `colors.conf` - **Auto-generated** colors.

- **`zsh/`** - Zsh shell configuration.
  - `aliases/` - Modular alias files.
  - `zsh_utils/helpers.sh` - Utility functions.

- **`nvim/`** - Neovim configuration.
- **`tmux/`** - Tmux configuration.
- **`vim/`** - Vim configuration.

#### Customization & System Configs
- **`customization/`** - General customization files.
  - `bin/wally` - **The Wallpaper/Theme Utility**.
  - `.config/gtk-3.0/` & `gtk-4.0/` - GTK settings (receiving Wallust colors).
  - `.config/qt5ct/` - Qt theming configuration.
  - `.config/nwg-look/` - GTK theme switcher.
  - `.config/xsettingsd/` - X settings daemon.
  - Root-level configs: `mimeapps.list`, `user-dirs.dirs`.

- **`others/`** - Miscellaneous configurations.
  - `.config/git/` - Git global config.
  - `.config/containers/` - Container policies.
  - `env/` - Development environment files.

- **`fonts/`** - Font configurations.

#### Development Tools
- **`pocman/`** - Custom package manager.
  - `bin/pocman` - Package manager executable.
  - `.config/pocman/` - Package lists.
- **`composer/`** - Composer config.
- **`obsidian/`** - Obsidian vault configs.

#### Platform-Specific
- **`mac-wm/`** - macOS window manager configs.
- **`mac_setup.sh`** & **`mac_install_packages.sh`** - macOS setup.

## How Stow Works

### Stow Package Structure

A stow package directory mirrors the target filesystem structure. For example:

```
zsh/
├── .zshrc
├── .zshenv
└── .config/
    └── zsh/
        └── custom.conf
```

When stowed, these files are symlinked to:
```
~/.zshrc -> ~/dotfiles/zsh/.zshrc
~/.zshenv -> ~/dotfiles/zsh/.zshenv
~/.config/zsh/custom.conf -> ~/dotfiles/zsh/.config/zsh/custom.conf
```

## Package Management (Pocman)

The repository uses `pocman` (`pocman/bin/pocman`) to manage system packages via TOML lists (`pocman/.config/pocman/arch.toml`).

*   `[cli:pacman]` - Core tools (git, stow, neovim).
*   `[desktop:pacman]` - GUI apps (hyprland, waybar, kitty).
*   `[desktop:yay]` - AUR packages (realesrgan-ncnn-vulkan-bin, wallust, swww).

## Integration Workflows

### The "Unified Theme" Pipeline
When a user changes a wallpaper via `wally`:
1. **Selection:** Image selected via Rofi.
2. **Processing:** Image is upscaled (if needed) -> Resized -> Cached.
3. **Generation:** `wallust run <image>` parses colors and fills templates in `~/.config/wallust/templates/`.
4. **Distribution:** Wallust writes config files to target directories (Hyprland, Waybar, etc.).
5. **Reloading:** `wally` sends signals:
   - `hyprctl reload` (Hyprland colors)
   - `SIGUSR2` (Waybar CSS)
   - `killall dunst` (Notifications)
   - `SIGUSR1` (Kitty colors)
   - `SIGUSR1` (Qt5ct)

### Adding a New Themed App
To add a new application to the unified theme system:
1. Create a template file in `wallust/.config/wallust/templates/` (e.g., `myapp.template`).
2. Use placeholders like `{{background}}`, `{{color4}}`.
3. Register the template in `wallust/.config/wallust/wallust.toml`:
   ```toml
   myapp = { template = "myapp.template", target = "~/.config/myapp/config" }
   ```
4. Configure the app to read that target file.

## Key Workflows

### Initial Setup
```bash
# One-liner installation
sh <(curl -sL https://itsemon245.github.io/dotfiles/install.sh)
```

### Changing Wallpapers & Themes
```bash
# Open the graphical picker
wally

# Force an upscale on a specific image
wally set ~/Wallpapers/anime.jpg -u
```

### Adding New Configurations
1. Create directory: `mkdir -p ~/dotfiles/myapp/.config/myapp`
2. Add config file: `touch ~/dotfiles/myapp/.config/myapp/config.json`
3. Stow it: `stow myapp`

### Updating Configurations
Edit files directly in `~/dotfiles/<package>/`. Changes are reflected immediately due to symlinks.

## Troubleshooting

### Colors not updating?
1. Check `~/.config/wallust/wallust.toml` paths.
2. Run `wallust run <image>` manually to check for template errors.
3. Ensure apps are importing the generated files (e.g., `@import "colors.css"` in Waybar).

### Wally upscaling failed?
1. Ensure `realesrgan-ncnn-vulkan-bin` is installed.
2. Check `~/.cache/wally` permissions.
3. Verify GPU drivers (Vulkan) are active.

### Symlink Conflicts
```bash
# Backup and remove existing file
mv ~/.config/app ~/.config/app.backup
cd ~/dotfiles
stow app
```
