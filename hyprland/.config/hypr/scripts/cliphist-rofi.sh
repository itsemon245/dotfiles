#!/usr/bin/env bash

# Script to show cliphist entries with image indicators in rofi
# For actual image previews, we'll use a custom rofi modi

PREVIEW_DIR="$HOME/.cache/cliphist-previews"
mkdir -p "$PREVIEW_DIR"

# Clean old previews (older than 1 hour)
find "$PREVIEW_DIR" -type f -mmin +60 -delete 2>/dev/null

# Function to check if entry is an image
is_image() {
    local hash="$1"
    cliphist decode "$hash" 2>/dev/null | file - 2>/dev/null | grep -qiE "(image|PNG|JPEG|GIF|WebP)"
}

# Function to create thumbnail
create_thumbnail() {
    local hash="$1"
    local preview_file="$PREVIEW_DIR/${hash}.png"
    
    if [[ ! -f "$preview_file" ]]; then
        cliphist decode "$hash" 2>/dev/null | \
            convert - -resize 200x200\> -quality 90 "$preview_file" 2>/dev/null
    fi
    
    if [[ -f "$preview_file" ]]; then
        echo "$preview_file"
    fi
}

# Function to get image info
get_image_info() {
    local hash="$1"
    cliphist decode "$hash" 2>/dev/null | file - 2>/dev/null | sed 's/.*: //'
}

# Get clipboard entries
entries=$(cliphist list)

# Process entries
declare -a rofi_lines
declare -a hash_map
declare -a preview_map

index=0
while IFS=$'\t' read -r hash content; do
    hash_map[$index]="$hash"
    
    if is_image "$hash"; then
        preview=$(create_thumbnail "$hash")
        info=$(get_image_info "$hash")
        if [[ -n "$preview" ]]; then
            preview_map[$index]="$preview"
            # Show image info with emoji
            rofi_lines[$index]="🖼️  $info"
        else
            rofi_lines[$index]="🖼️  $content"
            preview_map[$index]=""
        fi
    else
        rofi_lines[$index]="$content"
        preview_map[$index]=""
    fi
    
    ((index++))
done <<< "$entries"

# Save preview map for modi script
for i in "${!preview_map[@]}"; do
    if [[ -n "${preview_map[$i]}" ]]; then
        echo "${preview_map[$i]}" > "$PREVIEW_DIR/map_${i}.txt"
    fi
done

# Create modi script for preview
MODI_SCRIPT="$PREVIEW_DIR/cliphist-modi.sh"
cat > "$MODI_SCRIPT" << 'EOFMODI'
#!/usr/bin/env bash
PREVIEW_DIR="$HOME/.cache/cliphist-previews"

case "$1" in
    list)
        # Output the list
        cat
        ;;
    info)
        # Get preview for selected index
        selected_index="$ROFI_INFO"
        if [[ -n "$selected_index" && -f "$PREVIEW_DIR/map_${selected_index}.txt" ]]; then
            cat "$PREVIEW_DIR/map_${selected_index}.txt"
        fi
        ;;
esac
EOFMODI
chmod +x "$MODI_SCRIPT"

# Show in rofi - simple text format
selected=$(printf '%s\n' "${rofi_lines[@]}" | \
    rofi -modi "clipboard:$MODI_SCRIPT" -show clipboard \
    -theme ~/.config/rofi/launchers/type-4/style-6-clipboard.rasi \
    -dmenu -i -p "Clipboard" \
    -format 'i' \
    -selected-row 0)

# Cleanup
rm -f "$PREVIEW_DIR"/map_*.txt

# Get the hash of selected item and copy to clipboard
if [[ -n "$selected" && "$selected" =~ ^[0-9]+$ ]]; then
    selected_index=$selected
    if [[ -n "${hash_map[$selected_index]}" ]]; then
        cliphist decode "${hash_map[$selected_index]}" | wl-copy
    fi
fi
