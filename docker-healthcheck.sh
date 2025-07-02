#!/bin/bash
# Docker health check script for SharePoint Folder Size Calculator

# Check if the main process is running
if pgrep -f "sharepoint_folder_size.py" > /dev/null; then
    echo "Main process is running"
    exit 0
else
    # If not running, check if output files exist and are recent
    if [ -f "/output/folder_sizes_python.csv" ] && [ -f "/output/folder_sizes_python.json" ]; then
        # Check if files were modified in the last hour
        find /output -name "folder_sizes_python.*" -mmin -60 | grep -q . && exit 0
    fi
    echo "Health check failed"
    exit 1
fi