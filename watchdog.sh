#!/bin/bash
# Watchdog script for SharePoint Folder Size Calculator
# Monitors the application and restarts it if necessary

set -e

# Configuration
MAX_RETRIES=3
RETRY_DELAY=60
HEALTH_CHECK_INTERVAL=300

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log function
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if required environment variables are set
check_env() {
    local missing=0
    
    if [ -z "$TENANT_ID" ]; then
        log "${RED}ERROR: TENANT_ID not set${NC}"
        missing=1
    fi
    
    if [ -z "$CLIENT_ID" ]; then
        log "${RED}ERROR: CLIENT_ID not set${NC}"
        missing=1
    fi
    
    if [ -z "$CLIENT_SECRET" ]; then
        log "${RED}ERROR: CLIENT_SECRET not set${NC}"
        missing=1
    fi
    
    if [ -z "$SITE_URL" ]; then
        log "${RED}ERROR: SITE_URL not set${NC}"
        missing=1
    fi
    
    if [ -z "$FOLDER_PATH" ]; then
        log "${RED}ERROR: FOLDER_PATH not set${NC}"
        missing=1
    fi
    
    return $missing
}

# Run the main application
run_app() {
    log "${GREEN}Starting SharePoint Folder Size Calculator...${NC}"
    
    docker-compose run --rm python || return 1
    
    return 0
}

# Run health check
run_health_check() {
    log "${YELLOW}Running health check...${NC}"
    
    docker-compose run --rm python python health_check.py \
        --tenant-id "$TENANT_ID" \
        --client-id "$CLIENT_ID" \
        --site-url "$SITE_URL" || return 1
    
    return 0
}

# Main watchdog loop
main() {
    log "${GREEN}SharePoint Folder Size Calculator Watchdog Started${NC}"
    
    # Check environment variables
    if ! check_env; then
        log "${RED}Missing required environment variables. Exiting.${NC}"
        exit 1
    fi
    
    local retries=0
    local last_run=$(date +%s)
    
    while true; do
        # Check if it's time to run the application
        current_time=$(date +%s)
        time_since_last_run=$((current_time - last_run))
        
        # Run if it's been more than the health check interval
        if [ $time_since_last_run -ge $HEALTH_CHECK_INTERVAL ]; then
            # Run health check first
            if run_health_check; then
                log "${GREEN}Health check passed${NC}"
                
                # Check if output files are stale (older than 24 hours)
                if [ -f "output/folder_sizes_python.json" ]; then
                    file_age=$(((current_time - $(stat -c %Y "output/folder_sizes_python.json")) / 3600))
                    if [ $file_age -gt 24 ]; then
                        log "${YELLOW}Output files are $file_age hours old. Running update...${NC}"
                        
                        if run_app; then
                            log "${GREEN}Application completed successfully${NC}"
                            retries=0
                            last_run=$(date +%s)
                        else
                            log "${RED}Application failed${NC}"
                            retries=$((retries + 1))
                        fi
                    else
                        log "${GREEN}Output files are up to date ($file_age hours old)${NC}"
                    fi
                else
                    log "${YELLOW}Output files not found. Running application...${NC}"
                    
                    if run_app; then
                        log "${GREEN}Application completed successfully${NC}"
                        retries=0
                        last_run=$(date +%s)
                    else
                        log "${RED}Application failed${NC}"
                        retries=$((retries + 1))
                    fi
                fi
            else
                log "${RED}Health check failed${NC}"
                retries=$((retries + 1))
                
                # Try to run the app anyway if health check fails
                if [ $retries -le $MAX_RETRIES ]; then
                    log "${YELLOW}Attempting to run application (retry $retries/$MAX_RETRIES)...${NC}"
                    
                    if run_app; then
                        log "${GREEN}Application completed successfully${NC}"
                        retries=0
                        last_run=$(date +%s)
                    else
                        log "${RED}Application failed${NC}"
                    fi
                fi
            fi
            
            # Check if max retries exceeded
            if [ $retries -gt $MAX_RETRIES ]; then
                log "${RED}Max retries ($MAX_RETRIES) exceeded. Waiting before reset...${NC}"
                sleep $((RETRY_DELAY * 5))
                retries=0
            fi
        fi
        
        # Sleep before next check
        log "${YELLOW}Sleeping for $HEALTH_CHECK_INTERVAL seconds...${NC}"
        sleep $HEALTH_CHECK_INTERVAL
    done
}

# Handle signals
trap 'log "${YELLOW}Received signal, shutting down...${NC}"; exit 0' SIGTERM SIGINT

# Run main function
main