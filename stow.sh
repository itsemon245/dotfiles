#!/usr/bin/env bash
source colors.sh
cd ~/dotfiles

# Function to update status line (package name on first line, progress bar on second line)
update_status() {
    local status="$1"
    local package="$2"
    local current="${3:-0}"
    local total="${4:-0}"
    
    if [ $total -gt 0 ]; then
        local width=50
        local percentage=$((current * 100 / total))
        local filled=$((current * width / total))
        local empty=$((width - filled))
        
        # Build progress bar
        local bar=""
        local i
        for ((i=0; i<filled; i++)); do
            bar="${bar}█"
        done
        for ((i=0; i<empty; i++)); do
            bar="${bar}░"
        done
        
        # Clear first line and print status with package name (stay on first line)
        printf "\r\033[K${status}${CYAN}${package}${NC}"
        # Move to second line, clear and print progress bar
        printf "\033[1B\r\033[K${CYAN}[%s] %d/%d (%d%%)${NC}" "$bar" "$current" "$total" "$percentage"
        # Move back to first line for next update
        printf "\033[1A"
    else
        # No progress info, just print status
        printf "\r\033[K${status}${CYAN}${package}${NC}"
    fi
}

# Function to list directory names, excluding those in .installignore
list_dir() {
    find . -maxdepth 1 -mindepth 1 -type d | sed "s|^\./||" | sort -h | grep -v -x -f ./.installignore
}

# Function to create custom symlinks from symlinks.conf
create_custom_symlinks() {
    local config_file="$HOME/dotfiles/symlinks.conf"
    local symlink_count=0
    local success_count=0
    local fail_count=0
    
    # Get current user and group for ownership
    local current_user="${SUDO_USER:-$USER}"
    local current_group=$(id -gn "$current_user" 2>/dev/null || echo "$current_user")
    
    # Check if config file exists
    if [ ! -f "$config_file" ]; then
        return 0
    fi
    
    echo ""
    echo -e "${CYAN}Creating custom symlinks...${NC}"
    echo ""
    
    # Read config file line by line
    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comments and empty lines
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "${line// }" ]] && continue
        
        # Parse source:target pair
        if [[ "$line" =~ ^([^:]+):(.+)$ ]]; then
            local source_path="${BASH_REMATCH[1]}"
            local target_path="${BASH_REMATCH[2]}"
            
            # Resolve source path (relative to dotfiles root)
            local full_source="$HOME/dotfiles/$source_path"
            
            # Trim whitespace
            source_path=$(echo "$source_path" | xargs)
            target_path=$(echo "$target_path" | xargs)
            full_source=$(echo "$full_source" | xargs)
            
            # Skip if source doesn't exist
            if [ ! -e "$full_source" ]; then
                echo -e "${YELLOW}⚠ Source not found: ${source_path}${NC}"
                continue
            fi
            
            symlink_count=$((symlink_count + 1))
            
            # Check if target already exists
            if [ -e "$target_path" ]; then
                # If it's already the correct symlink, skip
                if [ -L "$target_path" ] && [ "$(readlink -f "$target_path")" = "$(readlink -f "$full_source")" ]; then
                    echo -e "${GREEN}✓ Already linked: ${CYAN}${source_path}${NC} → ${CYAN}${target_path}${NC}"
                    success_count=$((success_count + 1))
                    continue
                fi
                
                # If it's not a symlink, remove it (may need sudo for system directories)
                if [ ! -L "$target_path" ]; then
                    echo -e "${YELLOW}⚠ Removing existing file/directory: ${target_path}${NC}"
                    if [[ "$target_path" =~ ^/usr/ ]] || [[ "$target_path" =~ ^/etc/ ]]; then
                        # System directory, may need sudo
                        if sudo rm -rf "$target_path" 2>/dev/null; then
                            echo -e "${GREEN}  Removed (with sudo)${NC}"
                        else
                            echo -e "${RED}  ✗ Failed to remove (may need manual sudo)${NC}"
                            fail_count=$((fail_count + 1))
                            continue
                        fi
                    else
                        # User directory, no sudo needed
                        rm -rf "$target_path" 2>/dev/null || {
                            echo -e "${RED}  ✗ Failed to remove${NC}"
                            fail_count=$((fail_count + 1))
                            continue
                        }
                    fi
                else
                    # Existing symlink pointing elsewhere, remove it
                    rm -f "$target_path" 2>/dev/null || {
                        if [[ "$target_path" =~ ^/usr/ ]] || [[ "$target_path" =~ ^/etc/ ]]; then
                            sudo rm -f "$target_path" 2>/dev/null || {
                                echo -e "${RED}  ✗ Failed to remove existing symlink${NC}"
                                fail_count=$((fail_count + 1))
                                continue
                            }
                        else
                            echo -e "${RED}  ✗ Failed to remove existing symlink${NC}"
                            fail_count=$((fail_count + 1))
                            continue
                        fi
                    }
                fi
            fi
            
            # Create parent directory if it doesn't exist
            local target_parent=$(dirname "$target_path")
            if [ ! -d "$target_parent" ]; then
                if [[ "$target_path" =~ ^/usr/ ]] || [[ "$target_path" =~ ^/etc/ ]]; then
                    sudo mkdir -p "$target_parent" 2>/dev/null || {
                        echo -e "${RED}✗ Failed to create parent directory: ${target_parent}${NC}"
                        fail_count=$((fail_count + 1))
                        continue
                    }
                    # Set ownership of newly created parent directory
                    sudo chown -R "$current_user:$current_group" "$target_parent" 2>/dev/null
                else
                    mkdir -p "$target_parent" 2>/dev/null || {
                        echo -e "${RED}✗ Failed to create parent directory: ${target_parent}${NC}"
                        fail_count=$((fail_count + 1))
                        continue
                    }
                fi
            fi
            
            # Create symlink (may need sudo for system directories)
            if [[ "$target_path" =~ ^/usr/ ]] || [[ "$target_path" =~ ^/etc/ ]]; then
                # System directory, use sudo
                if sudo ln -sf "$full_source" "$target_path" 2>/dev/null; then
                    # Set ownership of symlink to current user
                    sudo chown -h "$current_user:$current_group" "$target_path" 2>/dev/null
                    echo -e "${GREEN}✓ Linked (sudo): ${CYAN}${source_path}${NC} → ${CYAN}${target_path}${NC}"
                    success_count=$((success_count + 1))
                else
                    echo -e "${RED}✗ Failed to link (sudo): ${source_path} → ${target_path}${NC}"
                    fail_count=$((fail_count + 1))
                fi
            else
                # User directory, no sudo needed
                if ln -sf "$full_source" "$target_path" 2>/dev/null; then
                    echo -e "${GREEN}✓ Linked: ${CYAN}${source_path}${NC} → ${CYAN}${target_path}${NC}"
                    success_count=$((success_count + 1))
                else
                    echo -e "${RED}✗ Failed to link: ${source_path} → ${target_path}${NC}"
                    fail_count=$((fail_count + 1))
                fi
            fi
        else
            echo -e "${YELLOW}⚠ Invalid format in symlinks.conf: ${line}${NC}"
        fi
    done < "$config_file"
    
    # Summary
    if [ $symlink_count -gt 0 ]; then
        echo ""
        if [ $fail_count -eq 0 ]; then
            echo -e "${GREEN}✓ Custom symlinks complete! (${success_count}/${symlink_count})${NC}"
        else
            echo -e "${YELLOW}⚠ Custom symlinks: ${success_count} succeeded, ${fail_count} failed${NC}"
        fi
    fi
}

# Function to remove conflicting files by trying to stow and handling errors
remove_conflicts() {
    local package_dir="$1"
    local status_prefix="$2"
    local current="$3"
    local total="$4"
    local conflicts_found=0
    local max_attempts=3
    local attempt=0
    
    # Try to stow, and if it fails due to conflicts, remove them and retry
    while [ $attempt -lt $max_attempts ]; do
        # Try to stow (this will fail if there are conflicts)
        if stow -n "$package_dir" >/dev/null 2>&1; then
            # No conflicts detected
            return 0
        fi
        
        # Stow failed, try to find and remove conflicts
        local found_conflict=0
        local conflict_count=0
        
        # Get all files that would be stowed
        while IFS= read -r item; do
            local rel_path="${item#./}"
            [ -z "$rel_path" ] && continue
            
            local target_path="$HOME/$rel_path"
            
            # If target exists and is NOT a symlink, it's a conflict
            if [ -e "$target_path" ] && [ ! -L "$target_path" ]; then
                found_conflict=1
                conflicts_found=1
                conflict_count=$((conflict_count + 1))
                
                # Update status to show conflict removal (cycling on same line)
                update_status "${status_prefix}${YELLOW}Removing conflicts ($conflict_count)... ${NC}" "$package_dir" "$current" "$total"
                
                if [ -d "$target_path" ]; then
                    rm -rf "$target_path" 2>/dev/null
                else
                    rm -f "$target_path" 2>/dev/null
                fi
            fi
        done < <(cd "$package_dir" && find . -mindepth 1 \( -type f -o -type d \) 2>/dev/null | sort)
        
        # If no conflicts found, break (might be a different error)
        [ $found_conflict -eq 0 ] && break
        
        attempt=$((attempt + 1))
    done
    
    return $conflicts_found
}

# List all directories and store them in a variable
directories=$(list_dir)
total_packages=$(echo "$directories" | wc -l)
current=0

echo -e "${CYAN}Installing dotfiles (${total_packages} packages)...${NC}"
# Print initial empty lines for status and progress bar
echo ""
echo ""

# Loop through each directory and stow it
while IFS= read -r dir; do
    if [ ! -d "$dir" ]; then
        continue
    fi
    
    current=$((current + 1))
    
    # Update status: Checking conflicts
    update_status "${CYAN}[$current/$total_packages] Checking conflicts: ${NC}" "$dir" "$current" "$total_packages"
    
    # Remove conflicting files before stowing
    status_prefix="${CYAN}[$current/$total_packages] ${NC}"
    if remove_conflicts "$dir" "$status_prefix" "$current" "$total_packages"; then
        update_status "${status_prefix}${GREEN}Conflicts resolved. Stowing: ${NC}" "$dir" "$current" "$total_packages"
    else
        update_status "${status_prefix}${CYAN}Stowing: ${NC}" "$dir" "$current" "$total_packages"
    fi
    
    # Stow the package (suppress output)
    if stow "$dir" >/dev/null 2>&1; then
        update_status "${status_prefix}${GREEN}✓ Stowed: ${NC}" "$dir" "$current" "$total_packages"
    else
        update_status "${status_prefix}${RED}✗ Failed: ${NC}" "$dir" "$current" "$total_packages"
    fi
    
    # Small delay for visual feedback
    sleep 0.1
    
done <<< "$directories"

# Final newline and completion message
echo ""
echo -e "${GREEN}✓ Dotfiles installation complete! (${total_packages} packages)${NC}"

# Create custom symlinks from symlinks.conf
create_custom_symlinks