local M = {
  buf = nil,
  win = nil,
}

local function valid_win(win)
  return win and vim.api.nvim_win_is_valid(win)
end

local function valid_buf(buf)
  return buf and vim.api.nvim_buf_is_valid(buf)
end

local function popup_in_tmux()
  if not vim.env.TMUX or vim.fn.executable("tmux") ~= 1 then
    return false
  end

  vim.fn.jobstart({
    "tmux",
    "display-popup",
    "-E",
    "-w",
    "90%",
    "-h",
    "90%",
    "-d",
    vim.fn.getcwd(),
    vim.o.shell,
  }, { detach = true })

  return true
end

local function terminal_opts()
  local width = math.floor(vim.o.columns * 0.9)
  local height = math.floor(vim.o.lines * 0.85)

  return {
    relative = "editor",
    style = "minimal",
    border = "rounded",
    width = width,
    height = height,
    row = math.floor((vim.o.lines - height) / 2),
    col = math.floor((vim.o.columns - width) / 2),
  }
end

function M.toggle()
  if popup_in_tmux() then
    return
  end

  if valid_win(M.win) then
    vim.api.nvim_win_close(M.win, true)
    M.win = nil
    return
  end

  if not valid_buf(M.buf) then
    M.buf = vim.api.nvim_create_buf(false, true)
    vim.bo[M.buf].bufhidden = "hide"
  end

  M.win = vim.api.nvim_open_win(M.buf, true, terminal_opts())

  if vim.bo[M.buf].buftype ~= "terminal" then
    vim.fn.termopen(vim.o.shell)
  end

  vim.cmd.startinsert()
end

return M
