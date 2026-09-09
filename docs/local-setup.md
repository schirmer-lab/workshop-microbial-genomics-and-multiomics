# Local setup

> These steps are only needed if you want to work on your own computer instead of the environment provided during the taught sessions. If you're a student in the workshop, you don't need to do anything here — see the [README](../README.md).

Dev container for the workshop **"Introduction to analysing microbial genomics and multi'omics data"** — Python, R and Jupyter with a full bioinformatics toolchain.

Run it either in **GitHub Codespaces** (no local install needed) or locally in **VS Code + Docker**.

## Requirements

> Not needed for GitHub Codespaces — skip to [Quick Start](#quick-start).

Before you can use this development environment, make sure you have the following installed:

### Essential Requirements
- **Docker Desktop** (v4.0+)
  - Windows: [Download Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
  - macOS: [Download Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
  - Linux: [Install Docker Engine](https://docs.docker.com/engine/install/) + [Docker Compose](https://docs.docker.com/compose/install/)

- **Visual Studio Code** (latest version)
  - [Download VS Code](https://code.visualstudio.com/download)

- **Dev Containers Extension** for VS Code
  - Install from VS Code: `Ctrl+Shift+X` → search "Dev Containers" → Install
  - Or [install directly](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### Platform-Specific Notes
- **Windows**: WSL2 is recommended for better Docker performance
- **macOS**: Ensure Docker Desktop has sufficient memory allocated (8GB+ recommended)
- **Linux**: User must be in the `docker` group to run Docker without sudo

### Storage Requirements
- **Available disk space**: ~15 GB. The image is ~3 GB to download but **~7 GB once unpacked**, plus the ~2 GB course dataset which extracts to another ~2.2 GB.
- **Data directory**: The container creates `~/biodata` on your host for persistent storage

## Quick Start

### GitHub Codespaces (recommended for students)

1. Click **Code → Codespaces → Create codespace on main**.
2. Wait for the container to start and the dataset to download. **First start takes a while** — the image and ~2 GB of data are fetched once.
3. Open any `dayN_labN_*.ipynb` and select the kernel (see below).

Students on the [GitHub Student Developer Pack](github-edu-info.md) get 180 Codespaces hours per month.

### Local VS Code + Docker

1. Open this project in VS Code.
2. When prompted, click **Reopen in Container**.
3. The environment is ready once the dataset download finishes.

> **Updating from a previous version**: rebuild the container with `Ctrl+Shift+P` → "Dev Containers: Rebuild Container" to pick up a new image tag.

## Container image

The dev container pulls a pre-built image from Docker Hub — nothing is built on your machine.

| | |
|---|---|
| Image | `schirmerlab/workshop-multiomics` (tag pinned in `.devcontainer/devcontainer.json`) |
| Built from | [`schirmer-lab/docker-images`](https://github.com/schirmer-lab/docker-images) → `schirmerlab/multiomics26/` |
| Versioning | date-based `YY.MM.DD`, with `.SNAPSHOT` until a build is verified |
| Architectures | `linux/amd64`, `linux/arm64` (Apple Silicon) |

> Previously `schirmerlab/biodev` (`1.1.x`). Never commit a `.SNAPSHOT` tag: those are local builds, are not pushed to Docker Hub, and a Codespace cannot pull one.

> The image definition lives in a **separate repository**. It used to be in a `docker/` directory here, but was moved out in October 2025. There is no `docker/` directory in this repo.

### Changing the environment

To add or remove a tool or package:

1. Edit `schirmerlab/multiomics26/environment.yml` in the `docker-images` repo.
2. Add a matching check to `test_environment.sh` in the same commit — the build fails if a declared tool is missing.
3. `./build.sh` to build and test locally.
4. `./build.sh --release --push` to publish.
5. Bump the tag in `.devcontainer/devcontainer.json` here.

See `schirmerlab/multiomics26/README.md` for full details.

### Data

The course data (~2 GB) is **not** in the image. It is downloaded to `/biodata` on first container start by `.devcontainer/download_biodata.sh`, from Zenodo with a Google Drive fallback. This keeps the image small and lets the dataset be updated without rebuilding.

If a download fails or you want to refresh it, delete `/biodata/resources` and rebuild the container.

See also: [platform support](platform-support.md) for details on Apple Silicon vs. Intel/AMD, and delivering the workshop in a teaching room.
