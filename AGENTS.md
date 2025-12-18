# Dotfiles Organization Guide

This document provides a comprehensive guide to understanding and working with this dotfiles repository structure and management system.

## Overview

This dotfiles repository uses **GNU Stow** for symlink-based configuration management. Each top-level directory represents a stow package that gets symlinked into the user's home directory (`~`). This provides:

- **Single source of truth** - All configs in one git repository
- **Easy synchronization** - Changes tracked via git
- **Modular organization** - Each application gets its own package directory
- **Cross-machine setup** - Clone and stow on any machine

## Repository Structure

### Core Files

- **`install.sh`** - Main installation script that:
  - Checks for and installs git if missing
  - Clones the repository to `~/dotfiles` if not present
  - Installs `stow` via pocman
  - Runs `stow.sh` to symlink all configurations
  - Installs packages via pocman
  - Sets up zsh and nvm

- **`stow.sh`** - Stows all directories by:
  - Finding all top-level directories
  - Filtering out directories listed in `.installignore`
  - Running `stow <directory>` for each valid directory

- **`colors.sh`** - Defines color variables (RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, NC) used by bash scripts

- **`.stow-local-ignore`** - Patterns for files/directories to exclude within stow packages:
  - Version control files (`.git`, `.gitignore`, `.svn`, etc.)
  - Backup files (`*.log`, `*~`, `#*#`)
  - Documentation files (`README.*`, `LICENSE.*`, `COPYING`)

- **`.installignore`** - Directories to exclude from stowing:
  - `.gitignore`
  - `.git`
  - `user`
  - `system`

### Stow Packages (Top-Level Directories)

Each directory in the root is a stow package that gets symlinked to `~`:

#### Application Configurations
- **`zsh/`** - Zsh shell configuration
  - `aliases/` - Modular alias files (git.sh, laravel.sh, tmux.sh, init.sh)
  - `exports.sh` - Environment variable exports
  - `ssh-agent.sh` - SSH agent setup
  - `zsh_utils/helpers.sh` - Utility functions
  - `.oh-my-zsh/` - Oh My Zsh framework (if present)

- **`nvim/`** - Neovim configuration
  - `minimal-init.lua` - Minimal Neovim config
  - `install-minimal-nvim.sh` - Installation script
  - `README.md` - Documentation

- **`kitty/`** - Kitty terminal emulator config

- **`tmux/`** - Tmux configuration
  - `tmux-installer/install.sh` - Tmux setup script
  - `tmux-cheatsheat.md` - Cheat sheet
  - `tmux.README.md` - Documentation

- **`vim/`** - Vim configuration

- **`dunst/`** - Dunst notification daemon config

- **`hyprland/`** - Hyprland window manager config
  - `check-dependencies.sh` - Dependency checker
  - `TROUBLESHOOTING.md` - Troubleshooting guide

- **`fonts/`** - Font configurations
  - `.config/fontconfig/fonts.conf` - Fontconfig settings

#### Customization & System Configs
- **`customization/`** - General customization files
  - Root-level configs: `QtProject.conf`, `appimagelauncher.cfg`, `greenclip.toml`, `mimeapps.list`, `user-dirs.dirs`, `user-dirs.locale`
  - `.config/` - Application configs:
    - `gtk-3.0/` - GTK3 settings
    - `gtk-4.0/` - GTK4 settings
    - `nautilus/` - File manager configs
    - `nwg-look/` - GTK theme switcher
    - `OpenRGB/` - RGB lighting config
    - `xsettingsd/` - X settings daemon
  - `scripts/` - Custom scripts (download_speed, memory, netspeed.go, vhost)

- **`others/`** - Miscellaneous configurations
  - `.config/` - Additional app configs:
    - `git/` - Git global config and template
    - `containers/` - Container policies
    - `ngrok/` - Ngrok tunnel config
  - `env/` - Development environment (Docker, PHP, PostgreSQL)

#### Development Tools
- **`composer/`** - Composer PHP package manager config

- **`obsidian/`** - Obsidian notes and vault

- **`pocman/`** - Custom package manager
  - `bin/pocman` - Package manager executable
  - `.config/pocman/` - Package lists (arch.toml with categorized packages)

#### Platform-Specific
- **`mac-wm/`** - macOS window manager configs

- **`mac_setup.sh`** - macOS-specific setup script

- **`mac_install_packages.sh`** - macOS package installation via Homebrew

#### Setup Scripts
- **`zsh-setup.sh`** - Sets up zsh, changes shell, installs Oh My Zsh plugins

- **`nvm-setup.sh`** - Installs Node Version Manager (nvm)

- **`distrobox.ini`** - Distrobox container configuration

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

### Adding New Configurations

1. **Create a new directory** in the root (e.g., `myapp/`)
2. **Mirror the target structure**:
   ```bash
   mkdir -p myapp/.config/myapp
   # Add config files
   touch myapp/.config/myapp/config.json
   ```
3. **Add to `.installignore`** if you don't want it stowed automatically
4. **Run `stow.sh`** or manually: `stow myapp`

### Excluding Files from Stow

Files matching patterns in `.stow-local-ignore` are excluded:
- Log files: `*.log`
- Version control: `.git`, `.gitignore`
- Backups: `*~`, `#*#`
- Documentation: `README.*`, `LICENSE.*`

## Package Management

### Pocman

The repository uses a custom package manager called `pocman` located in `pocman/bin/pocman`. It manages packages via TOML files:

- **`pocman/.config/pocman/arch.toml`** - Arch Linux package lists organized by:
  - Category: `cli`, `desktop`, `gaming`, `dev`, `fonts`
  - Package manager: `pacman`, `yay`, `paru`

Example:
```toml
[cli:pacman]
neovim
git
tmux

[desktop:yay]
google-chrome
greenclip
```

### Installation Flow

1. `install.sh` installs `stow` via pocman
2. `stow.sh` symlinks all configurations
3. `pocman --all` installs all packages from TOML files
4. Setup scripts configure zsh, nvm, etc.

## Platform Support

### Linux (Arch-based)
- Uses `pacman`, `yay`, `paru` via pocman
- Primary target platform

### macOS
- Uses Homebrew via `mac_install_packages.sh`
- Separate setup via `mac_setup.sh`
- Uses `mac-wm/` for window manager configs

## Key Workflows

### Initial Setup
```bash
# One-liner installation
sh <(curl -sL https://itsemon245.github.io/dotfiles/install.sh)

# Or manually
git clone https://github.com/itsemon245/dotfiles.git ~/dotfiles
cd ~/dotfiles
./pocman/bin/pocman install stow
source stow.sh
./pocman/bin/pocman --all
source zsh-setup.sh
source nvm-setup.sh
```

### Adding a New Application Config

1. Create package structure:
   ```bash
   mkdir -p ~/dotfiles/myapp/.config/myapp
   ```

2. Add configuration:
   ```bash
   cat > ~/dotfiles/myapp/.config/myapp/config.json << EOF
   {
     "setting": "value"
   }
   EOF
   ```

3. Stow it:
   ```bash
   cd ~/dotfiles
   stow myapp
   ```

4. Verify symlink:
   ```bash
   ls -la ~/.config/myapp/config.json
   # Should show: ~/.config/myapp/config.json -> ~/dotfiles/myapp/.config/myapp/config.json
   ```

5. Commit:
   ```bash
   git add myapp/
   git commit -m "Add myapp configuration"
   ```

### Adding to Existing Package

If adding to `customization/` or `others/`:

```bash
# Add file to existing package
echo "config" > ~/dotfiles/customization/.config/newapp/config.ini

# Restow the package
cd ~/dotfiles
stow -D customization  # Unstow first
stow customization     # Stow again
```

### Updating Configurations

1. Edit files directly in `~/dotfiles/<package>/`
2. Changes are immediately reflected (symlinks)
3. Commit changes:
   ```bash
   cd ~/dotfiles
   git add <package>/
   git commit -m "Update <package> configuration"
   ```

### Removing a Configuration

```bash
# Unstow (remove symlinks, keep files)
cd ~/dotfiles
stow -D <package>

# Or remove entirely
stow -D <package>
rm -rf ~/dotfiles/<package>
git add -A
git commit -m "Remove <package> configuration"
```

### Restowing All Packages

```bash
cd ~/dotfiles
source stow.sh
```

### Restowing Single Package

```bash
cd ~/dotfiles
stow -D <package>  # Unstow
stow <package>      # Stow again
```

## Best Practices

1. **Keep stow packages modular** - Each application/service gets its own directory
2. **Use `.config/` subdirectories** - For XDG-compliant configs
3. **Exclude generated files** - Add patterns to `.stow-local-ignore`
4. **Document package-specific setup** - Add README.md in package directories
5. **Test before committing** - Ensure stow works correctly
6. **Use version control** - All configs are tracked in git
7. **Handle conflicts** - Backup existing files before stowing

## Common Patterns

### XDG Config Directory
```bash
package/.config/appname/config.json
```

### Root-level Dotfile
```bash
package/.filename
```

### Scripts Directory
```bash
package/scripts/script.sh
```

### Nested Configs
```bash
customization/.config/gtk-3.0/settings.ini
others/.config/git/config
```

## Troubleshooting

### Symlink Conflicts
If a file already exists:
```bash
# Check what's there
ls -la ~/.config/app

# Backup and remove
mv ~/.config/app ~/.config/app.backup
cd ~/dotfiles
stow app
```

### Stow Not Working
```bash
# Check if stow is installed
which stow

# Verify directory structure
cd ~/dotfiles
ls -la package/

# Test stow with dry-run
stow -n -v package
```

### Files Not Being Stowed
- Check `.stow-local-ignore` for exclusion patterns
- Check `.installignore` if directory isn't being processed
- Verify directory structure matches target location
- Test with dry-run: `stow -n -v package`

### Stow Command Not Found
```bash
# Install stow
# Arch Linux
sudo pacman -S stow

# macOS
brew install stow

# Or via pocman
cd ~/dotfiles
./pocman/bin/pocman install stow
```

### Conflicting Symlinks
```bash
# Check for conflicts
cd ~/dotfiles
stow -n -v package

# Remove conflicting symlinks
rm ~/.conflicting-file

# Stow again
stow package
```

## Integration Tips

### With Git
All configurations are tracked:
```bash
cd ~/dotfiles
git status
git add <package>/
git commit -m "Description"
git push
```

### With Backup Systems
Since files are in `~/dotfiles/`, backing up this directory backs up all configs:
```bash
# Backup entire dotfiles
tar -czf dotfiles-backup.tar.gz ~/dotfiles
```

### With Multiple Machines
1. Clone repository on new machine
2. Run `install.sh` or `stow.sh`
3. All configs are symlinked and ready

## File Locations After Stowing

- `zsh/.zshrc` → `~/.zshrc`
- `customization/.config/gtk-3.0/settings.ini` → `~/.config/gtk-3.0/settings.ini`
- `nvim/minimal-init.lua` → `~/.config/nvim/init.lua` (if configured)
- `others/.config/git/config` → `~/.config/git/config`

Remember: The actual files remain in `~/dotfiles/`, and symlinks point to them from `~`.
