# Helper Layout Reference

## Canonical Structure

```text
tools/
  .local/bin/
    wally
    rofi-vpn

  .local/lib/dotfiles/
    shell/
      path.sh
      source.sh
      env.sh
      common.sh
    tool/
      log.sh
      command.sh
      cli.sh
      notify.sh
      common.sh
```

## Meaning

- `tools/.local/bin`: user-facing commands.
- `tools/.local/lib/dotfiles`: private sourced helper libraries for this dotfiles system.
- `shell/`: safe for startup files like `.zshrc`, `.bashrc`, and `exports.sh`.
- `tool/`: for executable Bash tools.
- `common.sh`: incubator for small helpers before a cohesive named module exists.

## Startup-Safe Helpers

Use `shell/` for functions that are safe to source in an interactive shell:

- `path.sh`: `path_prepend`, `path_append`, `path_remove`, `path_contains`
- `source.sh`: `source_if_exists`, `source_dir_if_exists`
- `env.sh`: `command_exists`, `is_interactive`, `has_display`
- `common.sh`: temporary startup-safe helpers

Startup-safe helper files must not print, exit, start background services, run desktop commands, or require optional dependencies at source time.

## Executable Tool Helpers

Use `tool/` for standalone Bash command helpers:

- `log.sh`: `info`, `warn`, `die`
- `command.sh`: `require_cmd`, `run`, `dry_run`
- `cli.sh`: usage and argument helper conventions
- `notify.sh`: notification adapter with command checks at call time
- `common.sh`: temporary executable-tool helpers

Executable helper files should also avoid source-time side effects. Functions can print or exit only when called by an executable script path that intends that behavior.

## Promotion Rule

Do not start by inventing a large taxonomy.

- One caller: keep logic local.
- One complex file: private function in that file.
- Two or more real callers: candidate for `common.sh` or an existing module.
- Coherent group in `common.sh`: move to a named module.
- Large `common.sh`: split by behavior before adding more unrelated helpers.

## Naming

Prefer boring names that describe behavior. Avoid clever project-specific abbreviations in helper names. Prefix only when needed to avoid collision or make call sites clearer.
