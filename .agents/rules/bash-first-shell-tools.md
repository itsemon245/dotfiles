# Bash-First Shell Tools Rule

## Default

Use Bash for dotfiles shell utilities, startup helpers, and desktop orchestration scripts by default.

This keeps helpers reusable across `.zshrc`, `.bashrc`, `exports.sh`, setup scripts, sourced libraries, and executable `bin` scripts without maintaining duplicate helper stacks in multiple languages.

## Helper Design

- Prefer small, boring helper files grouped by purpose, not one giant utility file.
- Use `common.sh` as a temporary incubator for small helpers before a cohesive named module exists.
- Source helper files only for function definitions and constants.
- Helper files must not print, exit the parent shell, mutate unrelated environment, or probe desktop/runtime dependencies at source time.
- Keep startup-safe helpers separate from executable-tool helpers.
- Use namespaced function names when ambiguity is likely.
- Add a helper only after the behavior is repeated across maintained files or meaningfully clarifies a complex script.
- Move functions out of `common.sh` when it grows large or when a group of functions has a clear shared purpose.

## Bash Limits

Bash cannot import one function without sourcing a file. Accept that limitation by keeping helper files small and side-effect-free. Do not build a large Bash framework to simulate a typed module system.

## Python Escape Hatch

A Bash tool may be refactored to Python only when Bash is the reason it is too large, unreadable, or hard to maintain.

The refactor must meet all of these conditions:

- It reduces total complexity or file size, or makes the control flow clearly easier to read.
- It avoids duplicating an equivalent helper stack in both Bash and Python.
- It uses `uv`/`uvx`-style script execution or a shebang that lets the file run like a normal `bin` command.
- It keeps shell startup helpers in Bash; Python must not be required just to start an interactive shell.
- It has a clear validation path matching or improving the Bash script behavior.

Do not move a tool to Python only for cleaner imports, type hints, or preference. The transition has to make the actual dotfiles easier to maintain.
