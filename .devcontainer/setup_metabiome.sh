#!/bin/bash
#
# Build the Metabiome environment and register its Jupyter kernel, so that
# day3_lab2_magraph_tutorial.ipynb works without any manual step.
#
# Runs from postCreateCommand, after the biodata download. Idempotent: if the
# kernel and the environment are already there it exits immediately, so a
# container restart costs nothing.
#
# Why this cannot go in the Dockerfile: the Metabiome source lives in THIS
# repository, not in the image build context (the image is built from
# schirmer-lab/docker-images). The environment also has to reference the
# workspace path, which does not exist at image build time.
#
# Three things this does differently from the old mdo_workshop_setup.sh:
#
#   1. Pins Python 3.12. Metabiome only requires >=3.11, so uv was free to pick
#      the newest managed interpreter -- currently 3.14 -- where cffi and
#      argon2-cffi-bindings have no prebuilt aarch64 wheels and fall back to
#      compiling. 3.12 has wheels for everything in the lock file.
#
#   2. Does not install the project itself (--no-install-project); the source is
#      put on sys.path with a .pth file instead. Installing it would compile the
#      Cython extensions in src/metabiome/optimized/, which needs a C compiler
#      the runtime image does not ship (`cc: No such file or directory`) --
#      build-essential is only in the image's build stage. day3_lab2 never calls
#      those functions: it uses metabiome.io and the MDS object (from_files,
#      groupby.var, filter.obs, agg), all pure Python. If you do need them:
#          cd Metabiome && uv sync --frozen && uv run python setup.py build_ext --inplace
#      on a machine that has gcc.
#
#   3. Drops `uv add ipykernel`. ipykernel is already a dependency in
#      pyproject.toml, and `uv add` rewrites pyproject.toml and uv.lock -- both
#      tracked files, so every student's clone came out dirty.
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="$REPO_DIR/Metabiome"
PYTHON_VERSION="3.12"
KERNEL_NAME="metabiome"
KERNEL_DISPLAY="Python (Metabiome)"
KERNEL_DIR="/usr/local/share/jupyter/kernels/$KERNEL_NAME"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] metabiome: $*"; }

if [ ! -d "$PROJECT_DIR" ]; then
    log "no Metabiome directory at $PROJECT_DIR -- nothing to do"
    exit 0
fi

if [ -f "$KERNEL_DIR/kernel.json" ] && [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
    log "kernel '$KERNEL_NAME' and environment already present -- skipping"
    exit 0
fi

if ! command -v uv >/dev/null 2>&1; then
    log "ERROR: uv is not installed in this image; cannot build the environment"
    exit 1
fi

cd "$PROJECT_DIR"

log "resolving dependencies with Python $PYTHON_VERSION (this takes a minute on first run)"
export UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-3000}"
# --frozen: never rewrite the tracked uv.lock.
uv sync --frozen --no-install-project --python "$PYTHON_VERSION"

VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

# Put src/ on sys.path instead of installing the project, avoiding the C build.
SITE_PACKAGES="$("$VENV_PYTHON" -c 'import site; print(site.getsitepackages()[0])')"
echo "$PROJECT_DIR/src" > "$SITE_PACKAGES/_metabiome_src.pth"
log "added $PROJECT_DIR/src to sys.path via $SITE_PACKAGES/_metabiome_src.pth"

log "registering the '$KERNEL_NAME' kernel"
"$VENV_PYTHON" -m ipykernel install --name "$KERNEL_NAME" --display-name "$KERNEL_DISPLAY"

# The name must match metadata.kernelspec.name in day3_lab2, or VS Code falls
# back to showing "Select Kernel".
if "$VENV_PYTHON" -c 'import metabiome.io' 2>/dev/null; then
    log "done -- day3_lab2 will open on '$KERNEL_DISPLAY'"
else
    log "WARNING: kernel registered, but 'import metabiome.io' failed"
    exit 1
fi
