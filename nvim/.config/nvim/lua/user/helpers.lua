local H = {}
function H.is_nixos()
  local file = io.open("/etc/os-release", "r")
  if not file then
    return false -- file doesn't exist, likely not NixOS
  end

  for line in file:lines() do
    if line:match('^NAME="NixOS"$') then
      file:close()
      return true
    end
  end

  file:close()
  return false
end

-- Modifies content of a file with search and replace
function H.modify_file_content(file_path, search_pattern, replacement)
  -- Step 1: Read the file contents
  local file = io.open(file_path, "r")
  if not file then
    print("Error: Could not open file " .. file_path)
    return
  end
  local content = file:read("*all")
  file:close()

  -- Debug: Print content and pattern to check if they match
  -- print("Original content:\n" .. content)
  -- print("Search pattern: " .. search_pattern)
  -- print("Replacement: " .. replacement)

  -- Step 2: Replace parts of the content
  local modified_content, num_replacements = content:gsub(search_pattern, replacement, 1)

  -- Debug: Check if any replacements were made
  -- print("Number of replacements: " .. num_replacements)
  if num_replacements == 0 then
    print("No matches found for the pattern.")
    return
  end

  -- Step 3: Write the modified content back to the file
  file = io.open(file_path, "w")
  if not file then
    print("Error: Could not write to file " .. file_path)
    return
  end
  file:write(modified_content)
  file:close()
end

-- Check if a server is installed using nix package manager
function H.is_server_installed(server, file_path)
  -- Execute `nix-env -q` to check if the package is installed
  local file = io.open(file_path, "r")
  if not file then
    print("Error: Could not open file " .. file_path)

    return
  end
  local content = file:read("*all")
  file:close()
  -- If result contains the server name, it means it's installed
  return content:find(server) ~= nil
end

function H.install_server(server, file_path)
  if not H.is_server_installed(server, file_path) then
    H.modify_file_content(file_path, "#new%-server%-here", server .. "\n    #new-server-here")
  end
end

function H.install_servers(file_path)
  local servers = require("user.lsp.servers")
  for i, server in pairs(servers) do
    -- Get the server name from server.nixpkg_name or key from servers table
    local server_name = server.nixpkg_name or i
    if not H.is_server_installed(server_name, file_path) then
      H.install_server(server_name, file_path)
      print("LSP Server " .. server_name .. " is added to your configuration.")
    else
      print("LSP Server " .. server_name .. " already exists in your configuration.")
    end
  end
  print("All LSP Servers are installed. Rebuild your system using nixos-rebuild switch to install the servers.")
end

-- Create a new nvim command
function H.create_command(cmd)
  vim.api.nvim_create_user_command(
  cmd.name,
  cmd.callback,
  {
    nargs = '*',    -- Allow zero or more arguments
    desc = cmd.desc or cmd.name .. " Command",    -- Description of the command
  }
)
end
return H
