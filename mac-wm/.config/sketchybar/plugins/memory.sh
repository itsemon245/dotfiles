#!/bin/bash

# Calculate memory usage
page_size=$(sysctl -n hw.pagesize)
used=$(vm_stat | grep "Pages active" | awk '{print $3}' | sed 's/\.//')
wired=$(vm_stat | grep "Pages wired down" | awk '{print $4}' | sed 's/\.//')
compressed=$(vm_stat | grep "Pages occupied by compressor" | awk '{print $5}' | sed 's/\.//')
total=$(sysctl -n hw.memsize)

used_bytes=$(( ($used + $wired + $compressed) * $page_size ))
used_gb=$(echo "scale=1; $used_bytes / 1073741824" | bc)
total_gb=$(echo "scale=1; $total / 1073741824" | bc)
remaining_gb=$(echo "scale=1; $total_gb - $used_gb" | bc)

sketchybar --set memory.free label="${remaining_gb}G"

