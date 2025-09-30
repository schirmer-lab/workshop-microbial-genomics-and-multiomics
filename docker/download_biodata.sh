#!/bin/bash

# Script to download biodata from Google Drive
# Only downloads if /biodata is empty to avoid unnecessary re-downloads

set -e  # Exit on any error

# Google Drive folder URL
DRIVE_URL="https://drive.google.com/drive/folders/15ju2h7LbzCKQH5iCEPb2tmAHwosCdc8U?usp=sharing"
BIODATA_DIR="/biodata"

# Function to log messages with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if directory is empty
is_directory_empty() {
    [ ! -d "$1" ] || [ -z "$(ls -A "$1" 2>/dev/null)" ]
}

# Function to install gdown if not available
install_gdown() {
    log "Installing gdown for Google Drive downloads..."
    if command -v pip3 >/dev/null 2>&1; then
        pip3 install gdown --quiet
    elif command -v pip >/dev/null 2>&1; then
        pip install gdown --quiet
    else
        log "ERROR: pip not found. Cannot install gdown."
        exit 1
    fi
}

# Function to extract folder ID from Google Drive URL
extract_folder_id() {
    local url="$1"
    # Extract folder ID from various Google Drive URL formats
    if [[ $url =~ folders/([a-zA-Z0-9_-]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        log "ERROR: Could not extract folder ID from URL: $url"
        exit 1
    fi
}

# Main execution
main() {
    log "Starting biodata download script..."
    
    # Create biodata directory if it doesn't exist
    mkdir -p "$BIODATA_DIR"
    
    # Check if biodata directory is empty
    if ! is_directory_empty "$BIODATA_DIR"; then
        log "Directory $BIODATA_DIR is not empty. Skipping download."
        log "If you want to re-download, please empty the directory first."
        exit 0
    fi
    
    log "Directory $BIODATA_DIR is empty. Proceeding with download..."
    
    # Check if gdown is available, install if not
    if ! command -v gdown >/dev/null 2>&1; then
        install_gdown
    fi
    
    # Extract folder ID from URL
    FOLDER_ID=$(extract_folder_id "$DRIVE_URL")
    log "Extracted folder ID: $FOLDER_ID"
    
    # Change to biodata directory
    cd "$BIODATA_DIR"
    
    # Download the folder contents as a zip file (much faster than individual files)
    log "Downloading Google Drive folder as zip archive to $BIODATA_DIR..."
    log "This may take a while depending on the folder size..."
    
    # Create a temporary directory for the zip file
    TEMP_DIR=$(mktemp -d)
    ZIP_FILE="$TEMP_DIR/biodata.zip"
    
    # Download the entire folder as a zip file
    if gdown --folder "https://drive.google.com/drive/folders/$FOLDER_ID" --output "$ZIP_FILE" --quiet; then
        log "Download completed. Extracting archive..."
        
        # Extract the zip file to the biodata directory
        log "Extracting archive..."
        if unzip -q "$ZIP_FILE" -d "$BIODATA_DIR"; then
            log "Archive extracted successfully!"
        else
            log "ERROR: Failed to extract archive. Please check if the download was successful."
            exit 1
        fi
        
        # Clean up temporary files
        rm -rf "$TEMP_DIR"
        
        # Check if extraction was successful
        if [ "$(ls -A "$BIODATA_DIR" 2>/dev/null)" ]; then
            log "Download completed successfully!"
            
            # List downloaded contents
            log "Downloaded contents:"
            ls -la "$BIODATA_DIR"
            
            # Set proper permissions for cross-platform compatibility
            log "Setting proper permissions..."
            find "$BIODATA_DIR" -type d -exec chmod 777 {} + 2>/dev/null || true
            find "$BIODATA_DIR" -type f -exec chmod 666 {} + 2>/dev/null || true
            
            log "Biodata setup completed successfully!"
        else
            log "ERROR: Extraction completed but no files found in $BIODATA_DIR"
            exit 1
        fi
    else
        log "ERROR: Download failed. Please check your internet connection and try again."
        log "You can also manually download the folder from: $DRIVE_URL"
        exit 1
    fi
}

# Run main function
# main "$@"
echo "Skipping download for now..."