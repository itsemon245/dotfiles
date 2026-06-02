# Tool Packaging and Workspace Ideas

This note captures deferred ideas that should not drive the main dotfiles refactor.

## Current Decision

The current plan follows the shell/Python boundary:

- Shell stays for interactive startup, sourced helpers, tiny wrappers, and shell-native installer glue.
- Python is the default for maintained user commands once they need structured parsing, subprocess orchestration, desktop adapters, cache/temp handling, or tests.
- Maintained commands live in `tools/.local/bin` and reusable Python logic lives in `tools/.local/lib/dotfiles_py/dotfiles_tools`.
- Startup-safe shell helpers live in `tools/.local/lib/dotfiles/shell`.

See `.agents/rules/shell-python-tools.md` for the rule and `.agents/skills/shell-python-tools` for the working skill.

## Deferred Ideas

These are not active choices for the current refactor:

- Go binaries for tools that need standalone compiled distribution.
- TypeScript or npm packages for npm-style dependency reuse.
- pnpm workspaces for multiple TypeScript packages.
- Nx for task graph caching or multi-package orchestration.
- GitHub releases or external package publishing.

## Decision Gate

Do not revisit these until:

- shared shell helpers are stable for real startup files;
- maintained commands such as `wally`, `rofi-vpn`, `rofi-cast`, and PHP/Composer wrappers are stable in the Python tool layout;
- one selected tool can be installed into a temporary prefix without stowing the whole dotfiles repo;
- the remaining complexity is clearly caused by local repo packaging limits, not by unfinished cleanup.
