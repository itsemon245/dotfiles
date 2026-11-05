# System Cleanup Tool Plan

A maintained command that reports reclaimable disk space, cleans it at explicit
levels, and warns before the disk fills. Working name: `sysclean`.

## Goals

- Show what can be reclaimed, and why it is safe, before anything is removed.
- Clean regenerable data at clear levels of aggressiveness.
- Run the safest level unattended, and warn early when space runs low.
- Make deleting the wrong thing structurally hard, not merely unlikely.

## Non-Goals

- Automatic worktree removal.
- Automatic Docker volume removal.
- Touching Steam libraries, game data, or anything under `/mnt`.
- Removing packages or uninstalling programs. Report candidates only.
- Running as root.
- Container health checks. That is a separate concern.

## Safety Rules

These hold at every level and are enforced in code.

1. **Preview by default.** No command changes anything without `--apply`.
2. **No shell.** Deletion uses `shutil.rmtree` and `subprocess.run` argument
   lists. Nothing passes through a shell, a glob, or string interpolation, so
   quoting and escaping cannot change the target.
3. **Fixed targets.** Each target is a declared rule. The tool never discovers
   deletion targets by searching.
4. **One guard for every path.** Before removal, a target must:
   - be a real directory, with its resolved path equal to its literal path;
   - sit under the expected base, with no `..` components;
   - not be the base itself, or a protected path;
   - contain no mount point;
   - not be in use by any process (cwd, exe, open file, or mapped file).
5. **Skip, never force.** A busy or unexpected target is skipped and reported.
   There is no `--force`.
6. **Docker by exact reference.** Images are removed with plain `docker rmi` by
   exact name or ID. No `prune`, no `-f`, never `-a`.
7. **Protected images.** `my/php:*` is always protected, because the `php` and
   `composer` wrappers use short-lived `--rm` containers and the image can look
   unused. Its base image and any image used by any container, including a
   stopped one, are also protected. Stop if a protected image disappears.
8. **Verify afterwards.** Report the real space freed and confirm targets are
   gone and protected items remain.

## Levels

Each level includes the ones below it.

| Level | Name | Contents | Unattended |
|---|---|---|---|
| 1 | `safe` | AUR build cache, dangling Docker images, stale temp and thumbnail files | Yes, weekly |
| 2 | `caches` | uv, npm, Gradle, pnpm store prune, browser caches, bundler caches | No; offered by the low-disk warning |
| 3 | `review` | Unused tagged Docker images, leftovers from removed apps | No; per-item confirmation |
| 4 | `report` | Worktrees, Docker volumes, orphaned packages, large games, models | Never; report only |

Level 2 costs a re-download, so it stays manual. Browser caches are skipped
while the browser runs. Clearing them does not sign anyone out, because cookies
live in the profile, not the cache.

## Commands

```text
sysclean report [--json]             Read-only report of all levels
sysclean clean --level N [--apply]   Preview, or apply with --apply
sysclean worktrees [--json]          Read-only worktree status
sysclean volumes                     Read-only summary of unattached volumes
sysclean watch                       Check free space and notify when low
```

Dependencies are checked only by the subcommand that needs them, at the point of
use, and never at import or startup. A missing tool names itself and how to get
it, and does not affect other subcommands.

| Subcommand | Required | Optional |
|---|---|---|
| `report` | None | `docker`, `git`, `gh`; a missing one marks that section unavailable |
| `clean` | None | `docker`; Docker rules are skipped and reported without it |
| `worktrees` | `git` | `gh`; PR status shows `unknown` without it |
| `volumes` | `docker` | None |
| `watch` | None | None |

`report` needs no network access.

The tool keeps working with as much as it can when a dependency is missing:

- Prefer stdlib over external commands. Sizes and process checks read the
  filesystem and `/proc` directly, so `du` and `lsof` are not needed.
- Each section or rule runs independently, so one failure cannot stop the rest.
- Output says what was skipped and why, and the exit code stays successful unless
  a removal itself failed.

Degrading must never weaken safety. A safety check that cannot run counts as
failed: the target is skipped, or its status becomes `unknown`. It never passes.

## Root-Owned Cleanup

The tool never needs root, because these are better solved by configuration.

| Item | Change |
|---|---|
| Pacman cache | `PACCACHE_ARGS='-k2'` in `/etc/conf.d/pacman-contrib`; `paccache.timer` is already enabled but keeps 3 versions |
| Coredumps | `/etc/systemd/coredump.conf.d/size.conf` with a `MaxUse=` cap |
| Journal | Already capped at 1000M; no change |

`report` shows their current size and the setting to change. The repo has no
package for `/etc` files yet, so the first version documents these steps.

## Worktrees

Report only. Removal stays a manual decision.

Each worktree gets a status from these checks. If a check cannot run, the status
becomes `unknown`, never `safe`.

- Uncommitted files, and whether each one already matches an upstream branch.
  Generated directories such as an untracked `node_modules` link do not count.
- Commits missing from every remote ref.
- PR state from `gh`, and ancestry against long-lived branches.
- Whether a process or Docker mount is using it.
- Whether an agent session owns it, and when that session was last active.
- Whether ignored `.env` files differ from the main checkout. Compare key names
  and value hashes, and never print values.

Lessons from the first audit:

- "Merged" by ancestry alone is unsafe. A worktree based on a merged commit can
  hold uncommitted work from a session active today.
- Reported sizes must count hardlinks. pnpm hardlinks made 104 worktrees look
  like 51G when removing them all would free 25G. An inode counts only when
  every link is inside the removal set.
- Never use `git status --ignored=matching` with `--untracked-files=no`. Git
  rejects the combination, and a helper that ignores the exit code reports no
  ignored files.
- Remotes may use SSH aliases, so the owner and repo cannot always be parsed
  from the URL. Show `unknown` rather than assuming there is no PR.

Claude app worktrees should be cleaned from the app, which keeps the session and
checks the branch out again on resume. Anything else needs a manual
`git worktree remove`, which refuses dirty trees.

## Low-Disk Warning

`sysclean watch` runs hourly from a user timer.

- Warn at 30G free, and send a critical notification at 10G. Both configurable.
- Include the largest quick win in the message, such as the size of Level 2.
- Notify once per threshold crossing, not every hour. Keep this state under
  `~/.local/state/sysclean/`.
- Never delete anything from this command.

This matters more than the ext4 reserve, which only acts when the disk is
already nearly full.

## Notifications

Unattended runs of `clean` and `watch` report through the framework in
`headless-notifications.md`, using `notify.post()`.

- `clean` reports what it freed, and anything it skipped.
- `watch` reports low-disk warnings, using a stable `key` so repeats replace
  each other.
- `--notify-start` adds a heads-up when work begins. It is off by default, and
  never waits for approval.
- A failed notification never fails the run.

## Layout

```text
tools/.local/bin/sysclean                          Tiny launcher
tools/.local/lib/dotfiles_py/dotfiles_tools/
  sysclean.py                                      CLI, levels, reporting
  sysclean_guard.py                                Path guard and removal
  sysclean_docker.py                               Image rules
  sysclean_worktrees.py                            Worktree audit
tools/.local/lib/dotfiles_py/tests/test_sysclean*.py
systemd/.config/systemd/user/sysclean.{service,timer}
systemd/.config/systemd/user/sysclean-watch.{service,timer}
```

- Stdlib only, reusing `cli.py`, `process.py`, `notify.py`, and `paths.py`.
- Add `--apply` locally. The shared `add_dry_run` helper defaults to making
  changes, which is the wrong default here.
- Generic rules live in code. This repo is public, so machine-specific paths,
  client project names, and extra protected images belong in an untracked
  `~/.config/sysclean/local.toml`, read with `tomllib`.
- The unit runs `sysclean clean --level 1 --apply`. Logs go to the journal.

## Testing

Tests must not be able to reach real data.

- Rules take an explicit base directory, and `--apply` on the real home requires
  the base to equal the running user's home.
- Every test uses a temp directory, and asserts that it is one.
- A throwaway tree covers hostile filenames (quotes, backslashes, `$(...)`,
  backticks, `*`, spaces), read-only directories, symlinks leading out of a
  target, a target that is itself a symlink, and sibling files that must survive.
- Docker and `gh` are mocked. A test confirms that `prune`, `-f`, and `-a` are
  never produced.
- Follow `.agents/rules/shell-python-tools.md`: `compileall`, `--help`, and
  launcher checks from a temp copied tree.

## Rollout

Each phase is reviewable and usable alone.

1. **Report.** `report`, `worktrees`, and `volumes`. Read-only, so low risk.
2. **Guard and Level 1.** Build `sysclean_guard.py` and its tests first, then
   add `clean --level 1`. Run it by hand for a while.
3. **Levels 2 and 3.** Add the cache rules, Docker rules, and per-item
   confirmation.
4. **Warning.** Add `watch` and its timer. This needs the notification framework.
5. **Automation.** Enable the weekly Level 1 timer after a few clean manual runs.
6. **System config.** Apply the pacman and coredump settings.

## Open Decisions

- Final command name.
- Whether the weekly timer deletes Level 1 data, or only notifies.
- Age limits, for example keeping AUR build files newer than 30 days.
- Whether `/etc` configuration gets its own package or stays documented.
