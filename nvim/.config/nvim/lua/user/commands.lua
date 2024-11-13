local H = require("user.helpers")
local nix_lsp_server_path = os.getenv("HOME").."/dotfiles/system/lsp/servers.nix"
H.create_command({
  name = "NLSPInstall",
  callback = function()
    H.install_servers(nix_lsp_server_path)
  end,
  desc = "Adds all lsp servers to the ~/dotfiles/system/lsp/servers.nix file from user.lsp.servers and builds the system",
})

