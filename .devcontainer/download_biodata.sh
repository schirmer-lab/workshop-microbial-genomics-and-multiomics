#!/bin/bash

# Script to download biodata resources from Zenodo / Google Drive
# Only downloads if /biodata/resources does not exist to avoid unnecessary re-downloads

set -e  # Exit on any error

# Google Drive URL for the resource folder zip archive
DRIVE_URL="https://drive.google.com/file/d/1U_wUnY-veNyYro1UqxI4JvwBImREnm38/view?usp=drive_link"
ZENODO_URL="https://zenodo.org/records/17285503/files/resources-251007_2200.zip?download=1"
BIODATA_DIR="/biodata"
RESOURCES_DIR="/biodata/resources"
PREFERRED_HOST="ZENODO"  # Options: "GOOGLE_DRIVE" or "ZENODO"

# Function to log messages with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if directory is emptym
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

# Function to extract ID from Google Drive URL
extract_drive_id() {
    local url="$1"
    local id=""

    # Try matching /d/<ID>
    if [[ "$url" =~ /d/([^/]+) ]]; then
        id="${BASH_REMATCH[1]}"

    # Try matching id=<ID> (e.g. for share links)
    elif [[ "$url" =~ id=([^&]+) ]]; then
        id="${BASH_REMATCH[1]}"

    else
        echo "ERROR: Unable to extract ID from URL: $url" >&2
        return 1
    fi

    echo "$id"
}

# Function to check if exrtaction was successful and set permissions
check_extraction_and_set_permissions() {
    if [ "$(ls -A "$1" 2>/dev/null)" ]; then
        log "Download completed successfully!"

        # List downloaded contents
        log "Downloaded contents:"
        ls -la "$1"

        # Set proper permissions for cross-platform compatibility
        log "Setting proper permissions..."
        find "$1" -type d -exec chmod 777 {} + 2>/dev/null || true
        find "$1" -type f -exec chmod 666 {} + 2>/dev/null || true

        log "Biodata setup completed successfully!"
    else
        log "ERROR: Extraction completed but no files found in $1"
        exit 1
    fi
}

# Main execution
main() {
    log "Starting biodata download script..."

    # Create biodata directory if it doesn't exist
    mkdir -p "$BIODATA_DIR"

    # Check if biodata directory is empty
    if [ -d "$RESOURCES_DIR" ]; then
        log "Directory $RESOURCES_DIR exists. Skipping download."
        log "If you want to re-download, please delete the directory first."
        exit 0
    fi

    log "Directory $RESOURCES_DIR does not exist. Proceeding with download..."

    if [ "$PREFERRED_HOST" == "ZENODO" ]; then
        log "Preferred host is ZENODO. Attempting to download from Zenodo..."

        # Change to biodata directory
        cd "$BIODATA_DIR"

        ZIP_FILE="$TEMP_DIR/resources.zip"

        # Download the entire folder as a zip file
        if wget --no-hsts "$ZENODO_URL" -O "$ZIP_FILE"; then
            log "Download completed. Extracting archive..."

            # Extract the zip file to the biodata directory
            log "Extracting archive..."
            if unzip -q "$ZIP_FILE" -d "$BIODATA_DIR"; then
                log "Archive extracted successfully!"
            else
                log "ERROR: Failed to extract archive. Please check if the download was successful."
                log "Otherwise, you can also manually download the folder from: $ZENODO_URL"
                exit 1
            fi

            # Check if extraction was successful
            check_extraction_and_set_permissions "$BIODATA_DIR"
            
        else
            log "ERROR: Download failed. Please check your internet connection and try again."
            log "You can also manually download the folder from: $ZENODO_URL"
            exit 1
        fi
    
    else
        log "Preferred host is GOOGLE_DRIVE. Attempting to download from Google Drive..."

        # Check if gdown is available, install if not
        if ! command -v gdown >/dev/null 2>&1; then
            log "gdown not found, attempting installation..."
            install_gdown
        fi

        # Extract folder ID from URL
        DRIVE_ID=$(extract_drive_id "$DRIVE_URL")
        log "Extracted google drive ID: $DRIVE_ID"

        # Change to biodata directory
        cd "$BIODATA_DIR"

        ## Download the folder contents as a zip file (much faster than individual files)
        #log "Downloading Google Drive folder as zip archive to $BIODATA_DIR..."
        #log "This may take a while depending on the folder size..."
        log "Downloading resources folder as zip archive from Google Drive to $BIODATA_DIR..."

        # Create a temporary directory for the zip file
        TEMP_DIR=$(mktemp -d)
        ZIP_FILE="$TEMP_DIR/resources.zip"

        # Download the entire folder as a zip file
        #if gdown --folder "https://drive.google.com/drive/folders/$DRIVE_ID" --output "$ZIP_FILE" --quiet; then
        # Download the pre-zipped folder from google drive  
        if gdown "$DRIVE_ID" --output "$ZIP_FILE"; then
            log "Download completed. Extracting archive..."

            # Extract the zip file to the biodata directory
            log "Extracting archive..."
            if unzip -q "$ZIP_FILE" -d "$BIODATA_DIR"; then
                log "Archive extracted successfully!"
            else
                log "ERROR: Failed to extract archive. Please check if the download was successful."
                log "Otherwise, you can also manually download the folder from: $DRIVE_URL"
                exit 1
            fi

            # Clean up temporary files
            rm -rf "$TEMP_DIR"

            # Check if extraction was successful
            check_extraction_and_set_permissions "$BIODATA_DIR"
        else
            log "ERROR: Download failed. Please check your internet connection and try again."
            log "You can also manually download the folder from: $DRIVE_URL"
            exit 1
        fi

    fi
    
}

# Run main function
main "$@"
#mkdir -p $BIODATA_DIR
#echo "Skipping download for now..."
