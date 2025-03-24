local M = {}

--- Get relative path to file
-- @param file (string, default='%') The file to get the relative path for
function M.relative_path(file)
	if file == nil then
		file = "%"
	end

	return vim.fn.fnamemodify(vim.fn.expand(file), ":p:~:.")
end

--- Create a floating window
function M.float(opts)
	local api = vim.api

	local buf = api.nvim_create_buf(false, true)

	api.nvim_buf_set_option(buf, "bufhidden", "wipe")

	local width = api.nvim_get_option("columns")
	local height = api.nvim_get_option("lines")

	local win_height = math.ceil(height * 0.8 - 4)
	local win_width = math.ceil(width * 0.8)

	local row = math.ceil((height - win_height) / 2 - 1)
	local col = math.ceil((width - win_width) / 2)

	if opts == nil then
		opts = {
			style = "minimal",
			relative = "editor",
			width = win_width,
			height = win_height,
			row = row,
			col = col,
			border = "rounded",
			-- noautocmd = true,
		}
	end

	for _, v in ipairs({ "q", "<esc>" }) do
		M.map({ "n", "v" }, v, ":close<cr>", {
			buffer = buf,
			nowait = true,
		})
	end

	local win = api.nvim_open_win(buf, true, opts)

	return buf, win
end

--- Calls `<Esc>` in normal mode
---
--- Necessary for visual range to be updated before executing
--- visual keymaps
function M.escape()
	vim.cmd.normal("�")
end

--- Wrapper around `vim.keymap.set` to include defaults
---
---@see vim.keymap.set()
---
---@param modes string|table the keymap mode
---@param lhs string left hand side
---@param rhs string|function right hand side
---@param opts nil|table options
function M.map(modes, lhs, rhs, opts)
	local defaults = {
		silent = true,
		noremap = true,
		expr = false,
		-- unique = true,
	}
	vim.keymap.set(modes, lhs, rhs, vim.tbl_extend("force", defaults, opts or {}))
end

--- Load VSCode user words into Neovim's spell file
--- Extracts words from .vscode/settings.json cSpell.userWords
function M.load_vscode_user_words()
	-- Find the project root directory with the .vscode folder
	local project_root = vim.fn.finddir('.vscode', '.;')

	if project_root ~= '' then
		-- Path to settings.json file
		local settings_file = project_root .. '/settings.json'

		-- Check if the settings.json file exists
		if vim.fn.filereadable(settings_file) == 1 then
			-- Read the file content
			local json = vim.fn.readfile(settings_file)
			local json_string = table.concat(json, '\n')

			-- Extract words from "cSpell.userWords"
			local user_words = {}
			local pattern = '"cSpell.userWords": %[(.-)%]'
			for word in string.gmatch(json_string, pattern) do
				for w in string.gmatch(word, '"(.-)"') do
					table.insert(user_words, w)
				end
			end

			-- Path to the spell file
			local spell_file = vim.fn.stdpath('config') .. '/spell/en.utf-8.add'

			-- Ensure the spell directory exists
			local spell_dir = vim.fn.stdpath('config') .. '/spell'
			if vim.fn.isdirectory(spell_dir) == 0 then
				vim.fn.mkdir(spell_dir, "p")
			end

			-- Read existing words from spell file to avoid duplicates
			local existing_words = {}
			if vim.fn.filereadable(spell_file) == 1 then
				local spell_content = vim.fn.readfile(spell_file)
				for _, line in ipairs(spell_content) do
					existing_words[line] = true
				end
			end

			-- Append only new words to the spellfile
			local new_words_added = false
			for _, word in ipairs(user_words) do
				if not existing_words[word] then
					vim.fn.writefile({word}, spell_file, 'a')
					existing_words[word] = true
					new_words_added = true
				end
			end

			-- Reload the spell file only if new words were added
			if new_words_added then
				vim.opt.spellfile = spell_file
				vim.cmd('silent mkspell! ' .. spell_file)
			end
			
			vim.opt.spell = true
		end
	end
end

--- Add a word to both Neovim's spell file and VSCode's settings.json
--- @param word string The word to add
function M.add_word_to_spell_and_vscode(word)
	if not word or word == "" then
		word = vim.fn.expand("<cword>")
	end
	
	-- First add to Neovim's spell file (default zg behavior)
	vim.cmd("silent! normal! zg")
	
	-- Now add to VSCode settings.json if it exists
	local project_root = vim.fn.finddir('.vscode', '.;')
	if project_root ~= '' then
		local settings_file = project_root .. '/settings.json'
		
		if vim.fn.filereadable(settings_file) == 1 then
			-- Read the settings file
			local json = vim.fn.readfile(settings_file)
			local json_string = table.concat(json, '\n')
			
			-- Check if the word is already in cSpell.userWords
			local user_words = {}
			local pattern = '"cSpell.userWords":%s*%[(.-)%]'
			local user_words_section = string.match(json_string, pattern)
			
			if user_words_section then
				-- Extract existing words
				for w in string.gmatch(user_words_section, '"([^"]+)"') do
					table.insert(user_words, w)
				end
				
				-- Check if word already exists
				local word_exists = false
				for _, w in ipairs(user_words) do
					if w == word then
						word_exists = true
						break
					end
				end
				
				-- Add the word if it doesn't exist
				if not word_exists then
					-- Add the word and sort alphabetically
					table.insert(user_words, word)
					table.sort(user_words)
					
					-- Determine the indentation level from the file
					local indent = "    " -- Default 4-space indent
					local indent_pattern = json_string:match('\n(%s+)"[^"]+":')
					if indent_pattern then
						indent = indent_pattern
					end
					
					-- Format the array with proper indentation
					local formatted_words = {}
					for i, w in ipairs(user_words) do
						formatted_words[i] = indent .. indent .. '"' .. w .. '"'
					end
					
					local words_str = table.concat(formatted_words, ",\n")
					local new_section = '"cSpell.userWords": [\n' .. words_str .. '\n' .. indent .. ']'
					
					-- Replace the userWords section in the JSON
					local new_json_string = string.gsub(json_string, 
						'"cSpell.userWords":%s*%[.-]', 
						new_section, 
						1)
					
					-- Write the updated JSON back to the file
					local new_json_lines = {}
					for line in string.gmatch(new_json_string, "[^\r\n]+") do
						table.insert(new_json_lines, line)
					end
					vim.fn.writefile(new_json_lines, settings_file)
					
					vim.notify('Added "' .. word .. '" to VSCode spell checker', vim.log.levels.INFO)
				end
			else
				-- cSpell.userWords doesn't exist yet, create it
				-- Determine the indentation level from the file
				local indent = "  " -- Default 2-space indent
				local indent_pattern = json_string:match('\n(%s+)"[^"]+":')
				if indent_pattern then
					indent = indent_pattern
				end
				
				local new_section = indent .. '"cSpell.userWords": [\n' .. 
								   indent .. indent .. '"' .. word .. '"\n' .. 
								   indent .. ']'
				
				-- Check if the file has a closing brace
				if json_string:match("}%s*$") then
					-- Add the new section before the closing brace
					local new_json_string = json_string:gsub("}%s*$", ",\n" .. new_section .. "\n}")
					
					-- Write the updated JSON back to the file
					local new_json_lines = {}
					for line in string.gmatch(new_json_string, "[^\r\n]+") do
						table.insert(new_json_lines, line)
					end
					vim.fn.writefile(new_json_lines, settings_file)
					
					vim.notify('Added "' .. word .. '" to VSCode spell checker', vim.log.levels.INFO)
				else
					vim.notify('Could not add word to VSCode settings: invalid JSON format', vim.log.levels.ERROR)
				end
			end
		end
	end
end

return M
