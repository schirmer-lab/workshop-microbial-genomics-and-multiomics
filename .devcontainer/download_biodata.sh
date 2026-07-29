#!/bin/bash
#
# Download the course data archive into /biodata.
#
# Runs from postCreateCommand in devcontainer.json. Skips the download entirely
# if /biodata/resources already exists, so rebuilding a container is cheap.
#
# Source order: Zenodo first, Google Drive as a fallback.
#
#   Zenodo serves a stable, versioned, unauthenticated URL with no rate limit
#   and needs nothing but wget. Google Drive throttles bulk downloads and needs
#   gdown to be pip-installed at container-create time -- which is exactly the
#   wrong failure mode when a lecture hall of students starts simultaneously.
#   multiomics25 had these the other way round.
#
set -euo pipefail

ZENODO_URL="https://zenodo.org/records/17285503/files/resources-251007_2200.zip?download=1"
DRIVE_URL="https://drive.google.com/file/d/1U_wUnY-veNyYro1UqxI4JvwBImREnm38/view?usp=drive_link"

BIODATA_DIR="/biodata"
RESOURCES_DIR="/biodata/resources"

TEMP_DIR=""

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

cleanup() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

# --- preflight -------------------------------------------------------------

require_unzip() {
    if command -v unzip >/dev/null 2>&1; then
        return 0
    fi
    log "ERROR: 'unzip' is not installed in this image."
    log "       Add it to packages-runtime.txt in schirmerlab/multiomics26."
    exit 1
}

# Extract the file ID from a Google Drive share URL.
extract_drive_id() {
    local url="$1"
    if [[ "$url" =~ /d/([^/]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    elif [[ "$url" =~ id=([^&]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        log "ERROR: could not extract a file ID from: $url"
        return 1
    fi
}

# --- download strategies ---------------------------------------------------
# Each returns 0 on success. They must not exit, so the caller can fall through
# to the next source.

download_from_zenodo() {
    log "Trying Zenodo..."
    wget --no-hsts --quiet --show-progress --tries=3 --timeout=60 \
         -O "$ZIP_FILE" "$ZENODO_URL"
}

download_from_drive() {
    log "Trying Google Drive..."

    if ! command -v gdown >/dev/null 2>&1; then
        log "Installing gdown..."
        if command -v pip3 >/dev/null 2>&1; then
            pip3 install gdown --quiet || return 1
        elif command -v pip >/dev/null 2>&1; then
            pip install gdown --quiet || return 1
        else
            log "pip not available; cannot install gdown."
            return 1
        fi
    fi

    local drive_id
    drive_id="$(extract_drive_id "$DRIVE_URL")" || return 1
    log "Google Drive file ID: $drive_id"

    gdown "$drive_id" --output "$ZIP_FILE"
}

# --- main ------------------------------------------------------------------

main() {
    log "Starting biodata setup..."

    mkdir -p "$BIODATA_DIR"

    if [ -d "$RESOURCES_DIR" ]; then
        log "$RESOURCES_DIR already exists -- skipping download."
        log "To force a re-download: rm -rf $RESOURCES_DIR"
        return 0
    fi

    require_unzip

    TEMP_DIR="$(mktemp -d)"
    ZIP_FILE="$TEMP_DIR/resources.zip"

    if download_from_zenodo; then
        log "Downloaded from Zenodo."
    elif download_from_drive; then
        log "Downloaded from Google Drive (Zenodo failed)."
    else
        log "ERROR: could not download the course data from either source."
        log "  Zenodo: $ZENODO_URL"
        log "  Drive : $DRIVE_URL"
        log "Download it manually and unzip it into $BIODATA_DIR"
        exit 1
    fi

    if [ ! -s "$ZIP_FILE" ]; then
        log "ERROR: the downloaded archive is empty."
        exit 1
    fi
    log "Archive size: $(du -h "$ZIP_FILE" | cut -f1)"

    log "Extracting..."
    if ! unzip -q "$ZIP_FILE" -d "$BIODATA_DIR"; then
        log "ERROR: extraction failed -- the download may be truncated or corrupt."
        exit 1
    fi

    # Guard against a "successful" extraction that produced nothing usable.
    if [ ! -d "$RESOURCES_DIR" ]; then
        log "ERROR: extraction finished but $RESOURCES_DIR was not created."
        log "Contents of $BIODATA_DIR:"
        ls -la "$BIODATA_DIR"
        exit 1
    fi

    # macOS zip cruft, if the archive still carries it.
    rm -rf "$BIODATA_DIR/__MACOSX"
    find "$BIODATA_DIR" -name '.DS_Store' -delete 2>/dev/null || true

    log "Setting permissions for cross-platform compatibility..."
    find "$BIODATA_DIR" -type d -exec chmod 777 {} + 2>/dev/null || true
    find "$BIODATA_DIR" -type f -exec chmod 666 {} + 2>/dev/null || true

    log "Contents of $RESOURCES_DIR:"
    ls -la "$RESOURCES_DIR"

    log "Biodata setup completed successfully."
}

main "$@"
