#!/bin/bash

# SharePoint Folder Size Calculator - Quick Run Script

echo "SharePoint Folder Size Calculator"
echo "================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create a .env file from .env.example"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Ask which implementation to use
echo "Which implementation would you like to use?"
echo "1) Python"
echo "2) Node.js"
read -p "Enter your choice (1 or 2): " choice

case $choice in
    1)
        echo "Running Python implementation..."
        docker-compose up python
        ;;
    2)
        echo "Running Node.js implementation..."
        docker-compose up nodejs
        ;;
    *)
        echo "Invalid choice. Please run again and select 1 or 2."
        exit 1
        ;;
esac