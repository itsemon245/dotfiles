#!/bin/bash

echo "=== Hyprland Dependency Checker ==="
echo ""

# Check NVIDIA packages
echo "Checking NVIDIA packages..."
pacman -Q nvidia nvidia-utils nvidia-settings 2>/dev/null || echo "❌ Missing NVIDIA packages"
pacman -Q nvidia 2>/dev/null && echo "✅ NVIDIA driver installed"

# Check Hyprland
echo ""
echo "Checking Hyprland..."
pacman -Q hyprland 2>/dev/null && echo "✅ Hyprland installed" || echo "❌ Hyprland not installed"

# Check essential Wayland packages
echo ""
echo "Checking Wayland packages..."
for pkg in waybar rofi dunst swww kitty xdg-desktop-portal-hyprland qt5-wayland qt6-wayland pipewire pipewire-pulse wireplumber libva-nvidia-driver; do
    pacman -Q "$pkg" 2>/dev/null && echo "✅ $pkg" || echo "❌ Missing: $pkg"
done

# Check kernel parameter
echo ""
echo "Checking kernel parameters..."
if grep -q "nvidia-drm.modeset=1" /proc/cmdline; then
    echo "✅ nvidia-drm.modeset=1 is set"
else
    echo "❌ nvidia-drm.modeset=1 is NOT set (CRITICAL!)"
    echo "   Add it to your bootloader configuration"
fi

# Check NVIDIA modules
echo ""
echo "Checking NVIDIA kernel modules..."
if lsmod | grep -q nvidia; then
    echo "✅ NVIDIA modules loaded"
    lsmod | grep nvidia | head -3
else
    echo "❌ NVIDIA modules not loaded"
fi

# Check NVIDIA status
echo ""
echo "Checking NVIDIA status..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader 2>/dev/null || echo "❌ nvidia-smi failed"
else
    echo "❌ nvidia-smi not found"
fi

# Check if running in Wayland
echo ""
echo "Current session:"
echo "XDG_SESSION_TYPE: ${XDG_SESSION_TYPE:-not set}"
echo "WAYLAND_DISPLAY: ${WAYLAND_DISPLAY:-not set}"

echo ""
echo "=== Check complete ==="

