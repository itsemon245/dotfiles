# Tool Packaging and Workspace Ideas

This note captures deferred ideas that should not drive the main dotfiles refactor.

## Current Decision

The current plan is Bash-first. Shared helpers should be implemented for shell startup files and executable shell tools before considering another language.

Python with `uv`/`uvx`-style execution is the only active escape hatch, and only when a Bash tool becomes too large, unreadable, or hard to maintain.

See `.agents/rules/bash-first-shell-tools.md` for the rule.

## Deferred Ideas

These are not active choices for the current refactor:

- Go binaries for tools that need standalone compiled distribution.
- TypeScript or npm packages for npm-style dependency reuse.
- pnpm workspaces for multiple TypeScript packages.
- Nx for task graph caching or multi-package orchestration.
- GitHub releases or external package publishing.

## Decision Gate

Do not revisit these until:

- shared shell helpers are used by real startup files and executable scripts;
- `exports.sh`, `.zshrc`, `wally`, and `rofi-vpn` have been debloated with the helper model;
- one selected tool can be installed into a temporary prefix without stowing the whole dotfiles repo;
- the remaining complexity is clearly caused by Bash limitations, not by unfinished cleanup.
