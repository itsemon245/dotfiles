#!/bin/bash

# Minimal Neovim Configuration Installer
# Usage: curl -sSL https://your-repo.com/install-minimal-nvim.sh | bash
# Or: wget -qO- https://your-repo.com/install-minimal-nvim.sh | bash
# Or: ./install-minimal-nvim.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NVIM_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/nvim"
BACKUP_DIR="$HOME/.nvim-backup-$(date +%Y%m%d-%H%M%S)"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    print_status "Checking requirements..."
    
    # Check if nvim is installed
    if ! command -v nvim &> /dev/null; then
        print_error "Neovim is not installed. Please install Neovim first."
        print_status "Install instructions:"
        print_status "  Ubuntu/Debian: sudo apt install neovim"
        print_status "  macOS: brew install neovim"
        print_status "  Arch: sudo pacman -S neovim"
        exit 1
    fi
    
    # Check nvim version
    local nvim_version=$(nvim --version | head -n1 | grep -oE 'v[0-9]+\.[0-9]+')
    print_status "Found Neovim $nvim_version"
    
    # Check if git is installed
    if ! command -v git &> /dev/null; then
        print_error "Git is not installed. Please install Git first."
        exit 1
    fi
    
    print_success "All requirements met!"
}

backup_existing_config() {
    if [[ -d "$NVIM_CONFIG_DIR" ]]; then
        print_warning "Existing Neovim configuration found."
        read -p "Do you want to backup your current config? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Creating backup at $BACKUP_DIR..."
            mkdir -p "$BACKUP_DIR"
            cp -r "$NVIM_CONFIG_DIR" "$BACKUP_DIR/"
            print_success "Backup created successfully!"
        else
            print_warning "Skipping backup. Your existing config will be overwritten."
        fi
        
        read -p "Continue with installation? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Installation cancelled."
            exit 0
        fi
    fi
}

create_minimal_config() {
    print_status "Creating minimal Neovim configuration..."
    
    # Create config directory
    mkdir -p "$NVIM_CONFIG_DIR"
    
    # Create the minimal init.lua
    cat > "$NVIM_CONFIG_DIR/init.lua" << 'EOF'
-- Minimal Neovim config for remote servers
-- Uses built-in plugin management - no external dependencies required

-- Basic Vim options
vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.tabstop = 4
vim.opt.shiftwidth = 4
vim.opt.expandtab = true
vim.opt.smartindent = true
vim.opt.wrap = false
vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.hlsearch = false
vim.opt.incsearch = true
vim.opt.termguicolors = true
vim.opt.scrolloff = 8
vim.opt.sidescrolloff = 8
vim.opt.mouse = "a"
vim.opt.clipboard = "unnamedplus"
vim.opt.splitbelow = true
vim.opt.splitright = true
vim.opt.swapfile = false
vim.opt.backup = false
vim.opt.undofile = true
vim.opt.updatetime = 50

-- Leader key
vim.g.mapleader = " "

-- Basic keymaps
vim.keymap.set("n", "<leader>pv", vim.cmd.Ex, { desc = "Open file explorer" })
vim.keymap.set("v", "J", ":m '>+1<CR>gv=gv", { desc = "Move selection down" })
vim.keymap.set("v", "K", ":m '<-2<CR>gv=gv", { desc = "Move selection up" })
vim.keymap.set("n", "J", "mzJ`z", { desc = "Join lines" })
vim.keymap.set("n", "<C-d>", "<C-d>zz", { desc = "Scroll down and center" })
vim.keymap.set("n", "<C-u>", "<C-u>zz", { desc = "Scroll up and center" })
vim.keymap.set("n", "n", "nzzzv", { desc = "Next search result and center" })
vim.keymap.set("n", "N", "Nzzzv", { desc = "Previous search result and center" })
vim.keymap.set("x", "<leader>p", [["_dP]], { desc = "Paste without overwriting register" })
vim.keymap.set({"n", "v"}, "<leader>y", [["+y]], { desc = "Yank to system clipboard" })
vim.keymap.set("n", "<leader>Y", [["+Y]], { desc = "Yank line to system clipboard" })
vim.keymap.set({"n", "v"}, "<leader>d", [["_d]], { desc = "Delete to void register" })
vim.keymap.set("n", "<C-k>", "<cmd>cnext<CR>zz", { desc = "Next quickfix item" })
vim.keymap.set("n", "<C-j>", "<cmd>cprev<CR>zz", { desc = "Previous quickfix item" })
vim.keymap.set("n", "<leader>k", "<cmd>lnext<CR>zz", { desc = "Next location list item" })
vim.keymap.set("n", "<leader>j", "<cmd>lprev<CR>zz", { desc = "Previous location list item" })
vim.keymap.set("n", "<Esc>", "<cmd>nohlsearch<CR>", { desc = "Clear search highlights" })

-- Window management
vim.keymap.set("n", "<C-h>", "<C-w><C-h>", { desc = "Move focus to the left window" })
vim.keymap.set("n", "<C-l>", "<C-w><C-l>", { desc = "Move focus to the right window" })
vim.keymap.set("n", "<C-j>", "<C-w><C-j>", { desc = "Move focus to the lower window" })
vim.keymap.set("n", "<C-k>", "<C-w><C-k>", { desc = "Move focus to the upper window" })

-- Simple plugin manager using built-in vim functionality
local function ensure_plugin(url, name)
    local install_path = vim.fn.stdpath("data") .. "/site/pack/plugins/start/" .. name
    if not vim.loop.fs_stat(install_path) then
        print("Installing " .. name .. "...")
        vim.fn.system({
            "git", "clone", "--depth=1", "--single-branch",
            url, install_path
        })
        vim.cmd("packloadall!")
        return true
    end
    return false
end

-- Install essential plugins (no external dependencies)
local plugins = {
    {"https://github.com/morhetz/gruvbox.git", "gruvbox"},
    {"https://github.com/windwp/nvim-autopairs.git", "nvim-autopairs"},
    {"https://github.com/numToStr/Comment.nvim.git", "comment"},
    {"https://github.com/tpope/vim-surround.git", "vim-surround"},
    {"https://github.com/tpope/vim-repeat.git", "vim-repeat"},
    {"https://github.com/nvim-lua/plenary.nvim.git", "plenary"}, -- needed for some plugins
}

-- Install missing plugins
local installed_any = false
for _, plugin in ipairs(plugins) do
    if ensure_plugin(plugin[1], plugin[2]) then
        installed_any = true
    end
end

-- If we installed new plugins, we need to restart to load them properly
if installed_any then
    print("New plugins installed. Please restart Neovim.")
    vim.defer_fn(function()
        vim.cmd("qa")
    end, 2000)
    return
end

-- Plugin configurations
-- Gruvbox colorscheme
vim.g.gruvbox_contrast_dark = "medium"
vim.g.gruvbox_sign_column = "bg0"
vim.cmd.colorscheme("gruvbox")

-- nvim-autopairs
local ok, autopairs = pcall(require, "nvim-autopairs")
if ok then
    autopairs.setup({
        check_ts = false, -- don't use treesitter
        disable_filetype = { "TelescopePrompt", "vim" },
    })
end

-- Comment.nvim
local comment_ok, comment = pcall(require, "Comment")
if comment_ok then
    comment.setup({
        padding = true,
        sticky = true,
        ignore = nil,
        toggler = {
            line = "gcc",
            block = "gbc",
        },
        opleader = {
            line = "gc",
            block = "gb",
        },
        extra = {
            above = "gcO",
            below = "gco",
            eol = "gcA",
        },
        mappings = {
            basic = true,
            extra = true,
        },
    })
end

-- Simple statusline
local function statusline()
    local mode = vim.fn.mode()
    local filename = vim.fn.expand('%:t')
    local filetype = vim.bo.filetype
    local line = vim.fn.line('.')
    local col = vim.fn.col('.')
    local total = vim.fn.line('$')
    local percent = math.floor((line / total) * 100)
    
    return string.format(
        " %s | %s | %s | %d:%d | %d%% ",
        mode:upper(),
        filename ~= "" and filename or "[No Name]",
        filetype ~= "" and filetype or "no ft",
        line,
        col,
        percent
    )
end

vim.opt.statusline = "%!v:lua.require'statusline'()"
_G.statusline = statusline

-- Auto commands
local augroup = vim.api.nvim_create_augroup("MinimalConfig", { clear = true })

-- Highlight on yank
vim.api.nvim_create_autocmd("TextYankPost", {
    group = augroup,
    callback = function()
        vim.highlight.on_yank({ timeout = 200 })
    end,
})

-- Remove trailing whitespace on save
vim.api.nvim_create_autocmd("BufWritePre", {
    group = augroup,
    pattern = "*",
    command = [[%s/\s\+$//e]],
})

-- Set filetype for common config files
vim.api.nvim_create_autocmd({"BufNewFile", "BufRead"}, {
    group = augroup,
    pattern = {"*.conf", "*.config"},
    command = "set filetype=conf",
})

-- Simple file explorer improvements
vim.g.netrw_browse_split = 0
vim.g.netrw_banner = 0
vim.g.netrw_winsize = 25
vim.g.netrw_localrmdir = 'rm -r'

-- Enable some useful built-in plugins
vim.cmd("filetype plugin indent on")
vim.cmd("syntax enable")

print("Minimal Neovim config loaded successfully!")
EOF

    print_success "Minimal configuration created at $NVIM_CONFIG_DIR/init.lua"
}

install_plugins() {
    print_status "Starting Neovim to install plugins automatically..."
    print_status "This may take a moment for first-time setup..."
    
    # Run nvim to trigger plugin installation
    nvim --headless -c "lua vim.defer_fn(function() vim.cmd('qa') end, 5000)" > /dev/null 2>&1 || true
    
    # Give it another try if needed
    nvim --headless -c "sleep 2" -c "qa" > /dev/null 2>&1 || true
    
    print_success "Plugin installation completed!"
}

show_usage() {
    print_success "Installation completed successfully!"
    echo
    print_status "Your minimal Neovim configuration includes:"
    echo "  • Gruvbox colorscheme"
    echo "  • Auto-pairs for brackets/quotes"
    echo "  • Comment toggling (gcc, gbc)"
    echo "  • Vim-surround for text objects"
    echo "  • Smart keymaps and options"
    echo "  • Custom statusline"
    echo
    print_status "Key bindings:"
    echo "  Space = Leader key"
    echo "  <leader>pv = File explorer"
    echo "  gcc = Toggle line comment"
    echo "  gbc = Toggle block comment"
    echo "  <leader>y = Copy to system clipboard"
    echo "  J/K (visual) = Move selection up/down"
    echo
    print_status "To start using: nvim"
    
    if [[ -n "$BACKUP_DIR" && -d "$BACKUP_DIR" ]]; then
        echo
        print_status "Your previous config was backed up to: $BACKUP_DIR"
    fi
}

# Main installation flow
main() {
    echo "========================================"
    echo "  Minimal Neovim Configuration Setup   "
    echo "========================================"
    echo
    
    check_requirements
    backup_existing_config
    create_minimal_config
    install_plugins
    show_usage
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Minimal Neovim Configuration Installer"
        echo
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --no-backup    Skip backup of existing configuration"
        echo
        echo "This script installs a minimal Neovim configuration with:"
        echo "  • No external dependencies (Node.js, Go, etc.)"
        echo "  • Essential plugins only"
        echo "  • Works great on remote servers"
        exit 0
        ;;
    --no-backup)
        SKIP_BACKUP=1
        ;;
esac

# Run the main installation
main

echo
print_success "🎉 Enjoy your minimal Neovim setup!"
