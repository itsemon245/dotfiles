#!/usr/bin/env bash
set -euo pipefail

GO="${1:-}"
SRC="/mnt/HDD/Installed Games"
DST="/mnt/HDD/Games"

# old_prefix_folder|new_clean_name
games=(
  "007 First Flight|007 First Flight"
  "god-of-war|God of War"
  "marvels-spider-man-miles-morales|Marvel's Spider-Man Miles Morales"
  "Red Dead Redemption 2|Red Dead Redemption 2"
  "Rise of the Tomb Raider|Rise of the Tomb Raider"
)

run() {
  printf '+ '
  printf '%q ' "$@"
  printf '\n'

  if [[ "$GO" == "--go" ]]; then
    "$@"
  fi
}

run mkdir -p "$DST/Installed" "$DST/Prefixes"

for row in "${games[@]}"; do
  IFS='|' read -r old_prefix new_name <<< "$row"

  old="$SRC/$old_prefix"
  games_dir="$old/drive_c/Games"
  old_game="$(find "$games_dir" -mindepth 1 -maxdepth 1 -type d -printf '%f\n')"

  old_game_path="$games_dir/$old_game"
  new_game="$DST/Installed/$new_name"
  new_prefix="$DST/Prefixes/$new_name"

  echo
  echo "== $old_prefix -> $new_name =="
  echo "game folder: $old_game"

  run mv "$old_game_path" "$new_game"
  run mv "$old" "$new_prefix"

  run mkdir -p "$new_prefix/drive_c/Games"
  run ln -s "$new_game" "$new_prefix/drive_c/Games/$old_game"

  run rm -f "$new_prefix/pfx"
  run ln -s . "$new_prefix/pfx"
done

echo
if [[ "$GO" == "--go" ]]; then
  echo "Done."
else
  echo "Dry run only. Run with: ./migrate-games.sh --go"
fi
