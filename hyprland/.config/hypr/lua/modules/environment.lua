---@param _settings Dotfiles.Settings
---@return nil
return function(_settings)
  hl.env("XCURSOR_SIZE", "32")
  hl.env("HYPRCURSOR_SIZE", "32")
  hl.env("QT_QPA_PLATFORMTHEME", "qt5ct")
  hl.env("XDG_CURRENT_DESKTOP", "Hyprland")
  hl.env("XDG_SESSION_TYPE", "wayland")
  hl.env("MOZ_ENABLE_WAYLAND", "1")
  hl.env("MOZ_DISABLE_RDD_SANDBOX", "1")
  hl.env("QT_QPA_PLATFORM", "wayland")
  hl.env("GTK_IM_MODULE", "ibus")
  hl.env("QT_IM_MODULE", "ibus")
  hl.env("XMODIFIERS", "@im=ibus")
  hl.env("LIBVA_DRIVER_NAME", "nvidia")
  hl.env("__GLX_VENDOR_LIBRARY_NAME", "nvidia")
  hl.env("NVD_BACKEND", "direct")
  hl.env("ELECTRON_OZONE_PLATFORM_HINT", "auto")
end
