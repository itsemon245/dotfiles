# Context: Fix `cast` shell script for Android → Arch Linux screencasting via ADB wireless debugging

## Goal
A shell script (`~/.local/bin/cast`) that:
1. Auto-detects the ADB wireless debugging port from the Android phone via avahi mDNS
2. Kills stale ADB state, reconnects, and launches scrcpy
3. Is invokable from rofi

## Environment
- **PC OS:** Arch Linux
- **Phone:** Xiaomi Pocophone F1 (POCO F1), Android 15
- **Phone IP:** 192.168.0.222 (DHCP-reserved, static)
- **Connection:** Both devices on same Wi-Fi (192.168.0.x subnet)
- **ADB pairing GUID:** adb-1a332f67-P1AaG0 (already permanently paired)
- **Tools available:** adb, scrcpy, avahi-daemon (running, bound to wlan0), rofi, notify-send

## Key facts about the setup
- Wireless Debugging port changes every session (every time the toggle is turned off/on or phone reboots)
- `avahi-browse -r _adb-tls-connect._tcp` successfully detects the current port when run manually
- `adb mdns services` does NOT work (unsupported in this adb build)
- `adb kill-server` / `adb start-server` / `adb disconnect` have been tried but ADB frequently gets stuck in `state=offline`
- `adb connect <ip>:<port>` always exits with code 0 even on failure — output string must be checked
- scrcpy works fine when ADB is manually connected beforehand

## Current (broken) script at ~/.local/bin/cast
```bash
#!/bin/bash
PHONE_IP="192.168.0.222"

notify-send "scrcpy" "Detecting ADB port..."

PORT=$(timeout 5 avahi-browse -r _adb-tls-connect._tcp 2>/dev/null \
    | grep "port = " \
    | grep -oP '\[\K[0-9]+' \
    | head -1)

if [ -z "$PORT" ]; then
    PORT=$(echo "" | rofi -dmenu -p "Could not detect port. Enter manually:")
    [ -z "$PORT" ] && exit 1
fi

adb kill-server
adb start-server 2>/dev/null
sleep 0.5

RESULT=$(adb connect "$PHONE_IP:$PORT" 2>&1)
if ! echo "$RESULT" | grep -q "connected to"; then
    notify-send "scrcpy" "ADB connect failed: $RESULT" --urgency=critical
    exit 1
fi

if ! adb devices | grep -q "$PHONE_IP:$PORT"; then
    notify-send "scrcpy" "Device not listed after connect!" --urgency=critical
    exit 1
fi

notify-send "scrcpy" "Casting Pocophone F1..."
scrcpy --window-title "Pocophone F1" --stay-awake
```

## Observed failures
- First run after a fresh ADB state: works
- After phone screen locks and reconnects: `WARN: Device disconnected` in scrcpy
- Subsequent runs: `ERROR: Device could not be connected (state=offline)` or `ERROR: Could not find any ADB device`
- `adb kill-server` + reconnect does not reliably fix offline state
- The port detected by avahi may be stale (from previous session) after a disconnect

## What needs fixing
1. Reliably escape `state=offline` — `adb kill-server` alone is not enough
2. Ensure the detected port is actually the current live port (not a cached stale one)
3. Handle the case where the phone disconnects mid-session and the script is re-run
4. Script should be fully automatic — no manual port input unless avahi genuinely fails

## Additional desired scrcpy flags
- `--stay-awake` (keep phone awake while casting)
- No `--turn-screen-off` (caused blank window issue when phone screen was already off)
- Navigation shortcut reminder: Ctrl+H=Home, Ctrl+B=Back, Ctrl+S=Recents (phone uses gesture nav, scrcpy keyboard shortcuts are used instead)
