# Hyprland 5.2 + NVIDIA RTX 3060 Ti Troubleshooting Guide

## Current Issues
- Black screen with cursor only
- Keyboard shortcuts not working
- dmabuf/EGLImage errors in logs

## Critical Checks

### 1. Kernel Parameters (REQUIRED)
You MUST have `nvidia-drm.modeset=1` in your kernel parameters.

**For GRUB:**
```bash
sudo nano /etc/default/grub
# Add to GRUB_CMDLINE_LINUX_DEFAULT:
GRUB_CMDLINE_LINUX_DEFAULT="... nvidia-drm.modeset=1"
sudo grub-mkconfig -o /boot/grub/grub.cfg
```

**For systemd-boot:**
Edit `/boot/loader/entries/arch.conf` and add `nvidia-drm.modeset=1` to options.

**Verify:**
```bash
cat /proc/cmdline | grep nvidia-drm.modeset
```

### 2. Required NVIDIA Packages
```bash
sudo pacman -S nvidia nvidia-utils nvidia-settings nvidia-prime
```

### 3. Required Hyprland Dependencies
```bash
sudo pacman -S hyprland waybar rofi dunst swww kitty \
  xdg-desktop-portal-hyprland qt5-wayland qt6-wayland \
  pipewire pipewire-pulse pipewire-alsa wireplumber \
  libva-nvidia-driver
```

### 4. Verify NVIDIA Driver Status
```bash
nvidia-smi
# Should show your GPU info, not errors

lsmod | grep nvidia
# Should show nvidia modules loaded
```

### 5. Check if NVIDIA is being used
```bash
glxinfo | grep "OpenGL renderer"
# Should show NVIDIA, not llvmpipe or AMD
```

## Configuration Fixes Applied

1. ✅ Removed invalid `layerrule = blur, NAMESPACE`
2. ✅ Added missing `animations.conf` source
3. ✅ Removed deprecated `resize_on_border`
4. ✅ Added NVIDIA environment variables
5. ✅ Enabled debug logging

## Environment Variables to Try

If still having issues, try these variations in `env.conf`:

**Option 1 (Current - try this first):**
```
env = GBM_BACKEND,nvidia-drm
env = WLR_RENDERER,vulkan
env = WLR_NO_HARDWARE_CURSORS,1
```

**Option 2 (If Option 1 fails, remove GBM_BACKEND):**
```
env = WLR_RENDERER,vulkan
env = WLR_NO_HARDWARE_CURSORS,1
env = __GLX_VENDOR_LIBRARY_NAME,nvidia
```

**Option 3 (If still failing, try software rendering):**
```
env = WLR_RENDERER,pixman
env = WLR_NO_HARDWARE_CURSORS,1
```

## Testing Steps

1. **From TTY (Ctrl+Alt+F2):**
   ```bash
   # Check logs
   journalctl -u display-manager -n 50
   
   # Try starting Hyprland manually
   export WLR_RENDERER=vulkan
   export WLR_NO_HARDWARE_CURSORS=1
   hyprland
   ```

2. **Check Hyprland logs:**
   ```bash
   cat ~/.local/share/hyprland/hyprland.log
   # or
   cat /tmp/hypr/*/hyprland.log
   ```

3. **Test with minimal config:**
   ```bash
   hyprland --config ~/.config/hypr/hyprland.conf
   ```

## Common Issues

### Black Screen with Cursor
- Usually means compositor started but can't render
- Check NVIDIA driver version (some versions >550 have issues)
- Verify kernel parameter is set
- Try different WLR_RENDERER values

### Keyboard Not Working
- Check if waybar/other apps are blocking input
- Verify input configuration in hyprland.conf
- Try starting without exec-once scripts

### dmabuf Errors
- EGL/OpenGL rendering issue
- Try WLR_RENDERER=vulkan instead of auto
- Check if libva-nvidia-driver is installed

## Arch Wiki Resources
- https://wiki.archlinux.org/title/NVIDIA
- https://wiki.archlinux.org/title/Hyprland
- https://wiki.archlinux.org/title/Wayland

## Most Likely Root Causes (Based on Your Errors)

### 1. Missing Kernel Parameter (MOST CRITICAL)
The `nvidia-drm.modeset=1` parameter is **absolutely required** for NVIDIA + Wayland.
Without it, you'll get black screens and rendering failures.

### 2. dmabuf/EGLImage Error
The error `"failed to import supplied dmabufs: Could not bind the given EGLImage to a CoglTexture2D"` suggests:
- EGL/OpenGL rendering issues
- Possibly wrong renderer backend
- Try `WLR_RENDERER=vulkan` (already set in config)

### 3. Missing Packages
Common missing packages:
- `libva-nvidia-driver` - for hardware video acceleration
- `xdg-desktop-portal-hyprland` - for Wayland integration
- `qt5-wayland` / `qt6-wayland` - for Qt apps

### 4. Startup Script Issues
The `exec-once` script launches waybar, swww, etc. If any of these fail, it might block startup.
Try commenting out the exec-once line temporarily to test.

## Testing with Minimal Config

Test with minimal config to isolate the issue:
```bash
hyprland --config ~/.config/hypr/hyprland-minimal.conf
```

## Next Steps if Still Failing

1. **FIRST**: Verify kernel parameter is set (most critical!)
2. Run `./check-dependencies.sh` to see what's missing
3. Check NVIDIA driver version compatibility
4. Try downgrading NVIDIA drivers if recently updated
5. Test with minimal config (no exec-once scripts)
6. Check if other Wayland compositors work (sway, wlroots-based)
7. Review full system logs: `journalctl -b -p err`
8. Check Hyprland logs: `cat ~/.local/share/hyprland/hyprland.log`

