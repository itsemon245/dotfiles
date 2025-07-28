#!/bin/bash

# Get total CPU usage (user + system)
cpu_usage=$(top -l 1 | grep "CPU usage" | awk '{print $3 + $5}' | sed 's/%//g')

# Update the SketchyBar item
sketchybar --set cpu.percent label="${cpu_usage}%"
