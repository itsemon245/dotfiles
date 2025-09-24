# Minimal Neovim Configuration

A lightweight Neovim configuration designed for remote servers and minimal setups. No external dependencies like Node.js, Go, or complex toolchains required!

## Features

✨ **Zero External Dependencies** - Works with just Neovim and Git
🎨 **Beautiful Gruvbox Theme** - Easy on the eyes
⚡ **Essential Plugins Only** - Fast startup and minimal resource usage
🔧 **Smart Defaults** - Sensible options and keymaps out of the box
📦 **Self-Installing** - Plugins install automatically on first run

## Quick Install

### One-liner Installation (Recommended)

```bash
# Using curl
curl -sSL https://raw.githubusercontent.com/your-username/dotfiles/main/nvim/install-minimal-nvim.sh | bash

# Using wget
wget -qO- https://raw.githubusercontent.com/your-username/dotfiles/main/nvim/install-minimal-nvim.sh | bash
```

### Manual Installation

1. Clone or download the `minimal-init.lua` file
2. Copy it to your Neovim config directory:
   ```bash
   mkdir -p ~/.config/nvim
   cp minimal-init.lua ~/.config/nvim/init.lua
   ```
3. Start Neovim - plugins will install automatically on first launch

### Local Installation

If you already have these files locally:

```bash
./install-minimal-nvim.sh
```

## Included Plugins

- **[gruvbox](https://github.com/morhetz/gruvbox)** - Retro groove color scheme
- **[nvim-autopairs](https://github.com/windwp/nvim-autopairs)** - Auto-close brackets, quotes, etc.
- **[Comment.nvim](https://github.com/numToStr/Comment.nvim)** - Smart commenting with `gcc` and `gbc`
- **[vim-surround](https://github.com/tpope/vim-surround)** - Surround text objects
- **[vim-repeat](https://github.com/tpope/vim-repeat)** - Better repeat support for plugins

## Key Bindings

| Key           | Action                             |
| ------------- | ---------------------------------- |
| `Space`       | Leader key                         |
| `<leader>pv`  | Open file explorer                 |
| `gcc`         | Toggle line comment                |
| `gbc`         | Toggle block comment               |
| `<leader>y`   | Copy to system clipboard           |
| `<leader>Y`   | Copy line to system clipboard      |
| `<leader>p`   | Paste without overwriting register |
| `J` (visual)  | Move selection down                |
| `K` (visual)  | Move selection up                  |
| `<C-h/j/k/l>` | Navigate between windows           |
| `<C-d/u>`     | Scroll half-page (centered)        |
| `n/N`         | Next/prev search (centered)        |
| `<Esc>`       | Clear search highlights            |

## Configuration Details

### Smart Defaults

- Line numbers (relative + absolute)
- 4-space indentation
- No swap files, undo files enabled
- Smart case-insensitive search
- System clipboard integration
- Automatic trailing whitespace removal

### Built-in Plugin Manager

Uses Neovim's native plugin loading system (`pack` directory) rather than external managers. Plugins are installed to:

```
~/.local/share/nvim/site/pack/plugins/start/
```

## Customization

The configuration is designed to be a solid starting point. To customize:

1. Edit `~/.config/nvim/init.lua`
2. Add your own keymaps, options, or plugins
3. Restart Neovim

## Troubleshooting

### First Launch

- Plugins install automatically on first run
- You may see a message "New plugins installed. Please restart Neovim."
- This is normal - just restart as instructed

### Plugin Issues

If plugins don't load:

```bash
# Remove plugin data and restart
rm -rf ~/.local/share/nvim/site/pack/plugins/
nvim  # Plugins will reinstall
```

### Network Issues

If git cloning fails:

- Check internet connection
- Try using the manual installation method
- Consider using a different git protocol

## Perfect For

- 🖥️ Remote servers and SSH sessions
- 🚀 Quick editing tasks
- 📝 Writing code without heavy toolchains
- 🔧 System administration
- ⚡ Fast, lightweight development

## Requirements

- Neovim 0.8+ (recommended 0.9+)
- Git
- Internet connection (for initial plugin installation)

Enjoy your minimal but powerful Neovim setup! 🎉
