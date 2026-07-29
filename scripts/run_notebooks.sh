#!/usr/bin/env bash
# =============================================================================
# Wrapper around scripts/run_notebooks.py.
#
# Works from either side of the container boundary:
#
#   * inside the dev container  -> runs directly
#   * on the host               -> reuses the running dev container if there is
#                                  one, otherwise starts a throwaway one from
#                                  the image pinned in devcontainer.json
#
# All arguments are passed straight through:
#
#   ./scripts/run_notebooks.sh --list
#   ./scripts/run_notebooks.sh --fast -v
#   ./scripts/run_notebooks.sh --only day3_lab5 --cell-timeout 7200
#
# The full suite is ~30 min, most of it day3_lab5's Flye/SPAdes/medaka assembly.
# --fast skips that one and finishes in ~12.
# =============================================================================

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEVCONTAINER="$REPO/.devcontainer/devcontainer.json"

# --- already inside the container? ------------------------------------------

if [ -d /biodata ] && [ -x /opt/conda/bin/python ]; then
    exec /opt/conda/bin/python "$REPO/scripts/run_notebooks.py" "$@"
fi

# --- host side --------------------------------------------------------------

command -v docker >/dev/null 2>&1 || {
    echo "docker not found, and this is not the dev container." >&2
    exit 1
}

# The image line in devcontainer.json (JSONC -- no jq, the file has comments).
IMAGE="$(sed -n 's/^[[:space:]]*"image"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$DEVCONTAINER" | head -1)"
[ -n "$IMAGE" ] || { echo "Could not read the image tag from $DEVCONTAINER" >&2; exit 1; }

# A running container that already has this repo bind-mounted: use it, so the
# run sees exactly the environment the notebooks are edited in.
CONTAINER=""
for c in $(docker ps -q); do
    if docker inspect -f '{{range .Mounts}}{{.Source}}{{"\n"}}{{end}}' "$c" 2>/dev/null | grep -qx "$REPO"; then
        CONTAINER="$c"
        break
    fi
done

if [ -n "$CONTAINER" ]; then
    WORKDIR="$(docker inspect -f "{{range .Mounts}}{{if eq .Source \"$REPO\"}}{{.Destination}}{{end}}{{end}}" "$CONTAINER")"
    echo "Using running container ${CONTAINER:0:12} ($(docker inspect -f '{{.Config.Image}}' "$CONTAINER")) at $WORKDIR"
    exec docker exec -w "$WORKDIR" "$CONTAINER" /opt/conda/bin/python "$WORKDIR/scripts/run_notebooks.py" "$@"
fi

# Nothing running: throwaway container with the same mounts the dev container uses.
WORKDIR="/workspaces/$(basename "$REPO")"
echo "No running dev container found; starting a throwaway $IMAGE"
[ -d "$HOME/biodata/resources" ] || echo "WARNING: $HOME/biodata/resources does not exist -- most notebooks will fail." >&2

exec docker run --rm -t \
    -v "$REPO:$WORKDIR" \
    -v "$HOME/biodata:/biodata" \
    -w "$WORKDIR" \
    "$IMAGE" \
    /opt/conda/bin/python "$WORKDIR/scripts/run_notebooks.py" "$@"
