---@param settings Dotfiles.Settings
---@return nil
return function(settings)
  hl.on("hyprland.start", function()
    hl.exec_cmd(settings.commands.startup)
    hl.exec_cmd(settings.commands.clipboard_text_watcher)
    hl.exec_cmd(settings.commands.clipboard_image_watcher)
  end)
end
