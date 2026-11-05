# Headless Notifications Plan

A small framework that lets unattended services report what they did without
needing a desktop session. A service writes a message to a file, and a relay
shows it through whatever notifier is active.

## Goals

- Any background service can notify with one call, and no setup.
- Messages survive having no session, a logged-out user, or a notifier restart.
- Lean and easy to maintain: no daemon, no third-party dependency.
- Not tied to a notifier. Delivery uses the freedesktop notification standard.

## Non-Goals

- Asking for approval or cancelling work. Notifications are informational.
- Replacing direct notifications in interactive tools such as `wally`.
- Messages from other machines. The file format leaves this open for later.

## Why Not Notify Directly

Direct notifications from user services work while a session is running, but
are lost when:

- nobody is logged in, since lingering keeps timers running without a desktop;
- dunst is restarting, which `wally` causes on every theme change.

Writing a file needs no bus, display, or notifier.

## Design

```text
service -> notify.post() -> inbox/<file>.json
                                 |
             notify-relay.path --+-- hypr-startup, after dunst starts
                                 v
                           notify-relay -> notify.notify() -> dunst
                                 |
                                 v
                        sent/<service>.jsonl
```

### Storage

Under `$XDG_STATE_HOME/notify/`, which survives reboots:

- `tmp/`: messages being written
- `inbox/`: complete messages waiting for delivery
- `sent/<service>.jsonl`: delivered history, one line per message
- `rejected/`: malformed messages, kept for debugging

There is one shared inbox because a systemd path unit cannot watch subfolders.
One inbox also means a new service needs no registration. Per-service history
comes from the `service` field.

### Message Format

One JSON object per file. Only `service` and `title` are required, and optional
fields are left out when unused.

```json
{"service":"sysclean","title":"🧹 Weekly cleanup finished","body":"Freed 4.2G.","icon":"user-trash","urgency":"normal","key":"sysclean-weekly","expires":"2026-11-12T10:00:00+06:00"}
```

| Field | Meaning |
|---|---|
| `service` | Sender name; must match `[a-z0-9-]+` |
| `title` | Heading; emoji are plain text here |
| `body` | Optional detail |
| `icon` | Optional freedesktop icon name |
| `urgency` | `low`, `normal` (default), or `critical` |
| `key` | Optional; a newer message with the same key replaces the older one |
| `expires` | Optional; the relay drops the message after this time |

JSON is deliberate. These messages are about 200 bytes and rare, and ext4 stores
each file in a 4K block, so a binary format saves no disk space. It would also
add a third-party dependency, stop `cat` and `jq` from reading messages, and make
it hard for shell scripts to write them.

Files are named `<epoch-ns>-<service>-<pid>.json`, which sorts by time. The name
is built only from validated parts, so message content can never affect a path.

### Writing

`notify.post()` writes to `tmp/`, then renames into `inbox/`, so the relay never
sees half a message.

It must never break the calling service. If the write fails, it logs to stderr
and returns `False`, because a cleanup should not fail over a notification.

`notify-post` wraps the same function for shell scripts.

### Delivery

`notify-relay` is a one-shot command. It holds a lock, because the path unit and
the login flush can run together.

1. Ask the session bus whether `org.freedesktop.Notifications` has an owner,
   without activating it. If not, exit and leave the inbox alone.
2. Read messages oldest first. Move malformed or oversized files to `rejected/`.
3. Drop expired messages. For each `key`, keep only the newest.
4. Deliver with `notify.notify()`, passing `key` as the stack tag.
5. On success, append to `sent/<service>.jsonl` and remove the inbox file.
   On failure, leave it and stop, so the next run retries.
6. Prune history older than 30 days.

The relay rescans until the inbox is empty, because a path unit cannot see files
that land while the relay runs. `--wait` gives a restarting notifier time to
return before messages are left queued.

Content is only passed as argument list items, never through a shell. Text is
escaped because dunst runs with `markup = full`, and `--` goes before the title
so a title starting with `-` is not read as an option. A key shown on screen
replaces the previous notification through dunst's stack tag, even when the
messages were delivered separately.

### Triggers

- `notify-relay.path` uses `PathChanged=` on the inbox. `DirectoryNotEmpty=`
  would retrigger in a loop while messages wait for a session.
- `hypr-startup` runs `notify-relay` once after starting dunst, which delivers
  anything queued while away. `graphical-session.target` is not active on this
  setup, so it cannot be used for this.

## Graceful Degradation

Each part works with what is available, and nothing here needs a dependency that
stdlib Python and systemd do not provide.

- Notifier fallback is `dunstify`, then `notify-send`, then `hyprctl notify`.
- With no notifier, messages wait in the inbox.
- With no relay installed, messages still accumulate safely, and interactive use
  is unaffected.

`notify.notify()` currently returns nothing and hides failures. It needs to
return whether delivery worked, or the relay would delete undelivered messages.
Existing callers can ignore the return value.

## Start-of-Work Notifications

Services notify when they finish or need attention. A start notification is
opt-in per tool, with a flag such as `--notify-start`, and is off by default. It
is only a heads-up.

## Layout

```text
tools/.local/bin/notify-post
tools/.local/bin/notify-relay
tools/.local/lib/dotfiles_py/dotfiles_tools/notify.py        post(), return values
tools/.local/lib/dotfiles_py/dotfiles_tools/notify_relay.py
tools/.local/lib/dotfiles_py/tests/test_notify_queue.py
systemd/.config/systemd/user/notify-relay.{path,service}
```

## Testing

- Use a temp `XDG_STATE_HOME` and a fake notifier, so no real notification fires.
- Cover hostile titles and bodies (quotes, backslashes, `$(...)`, markup, newlines).
- Confirm bad service names are rejected, and cannot escape the inbox.
- Confirm a failed delivery keeps the message, and retries.
- Confirm expiry, `key` replacement, ordering, and malformed files.
- Confirm a `post()` write failure does not raise.
- Test on the real system that a rename into the inbox fires `PathChanged=`.
- Test whether calling the notifier with no session starts dunst, which is why
  the relay checks for an owner first.

## Rollout

1. Done: `notify.post()`, `notify-post`, and the `notify.notify()` return value.
2. Done: `notify-relay` and its tests.
3. Done: the path unit and the `hypr-startup` flush.
4. Next: adopt it in `sysclean`, the first real user.

## Open Decisions

- Whether to collapse many queued messages into one summary per service at login.
- How long to keep history. The default is 30 days.
