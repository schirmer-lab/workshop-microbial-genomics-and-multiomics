# Environmental Multi-omics Workshop

Dev container for the TUM course **"Introduction to analysing microbial genomics and multi'omics data"** — Python, R and Jupyter with a full bioinformatics toolchain.

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

Students on the [GitHub Student Developer Pack](docs/github-edu-info.md) get 180 Codespaces hours per month.

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

> Previously `schirmerlab/biodev` (`1.1.x`). The pin is currently a local `.SNAPSHOT` build under verification — it is **not on Docker Hub**, so a Codespace created from this commit cannot start. Release it (see the checklist in `devcontainer.json`) before pushing to `main`.

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

## Kernels

The container ships exactly two kernels, and every notebook declares the one it needs in its own metadata:

| Kernel | Shown as | Used by |
|---|---|---|
| `ir` | **R** | all R notebooks |
| `python3` | **Python 3.10** | all Python notebooks except `day3_lab2` |
| `metabiome` | **Python (Metabiome)** | `day3_lab2` only — built automatically on container create |

Because the declared kernel name matches an installed one, VS Code pre-selects it when you open the notebook; you should not have to choose. If it still shows **Select Kernel**, click it → **Jupyter Kernel...** and pick the kernel named in the table above. The R kernel is listed under "Jupyter Kernels" as plain **R**, not under a language-specific group.

> Do not "fix" a notebook by saving it with a different kernel — the metadata is what makes the pre-selection work for the next student.

## Working with R Notebooks

### R Language Server

The first time you work with R files, you might see a popup asking about installing the R `languageserver` package. This has been **pre-installed** in the container to provide enhanced R features like:
- Code completion and IntelliSense
- Function signatures and documentation
- Error detection and linting

If you still see this popup, simply click "Yes" or "No" based on your preference - the package is already available.

### Troubleshooting

**Can't find the R kernel?**
- Ensure you're looking in the "Jupyter Kernels" section, not other categories
- Try refreshing the kernel list or restarting VS Code
- Verify the dev container has fully loaded (check the bottom-left corner for "Dev Container" indicator)

**R code not executing?**
- Make sure you've selected the R kernel (see instructions above)
- Check that the cell type is set to "Code" not "Markdown"

## Notebooks

| Notebook | Kernel | Topic |
|---|---|---|
| `day1_lab0_hello_world_r.ipynb` | R | R warm-up, package check |
| `day1_lab1_intro_to_R_set2R.ipynb` | R | Introduction to R |
| `day1_lab1_test_setup_R_env.ipynb` | R | Environment self-test |
| `day1_lab2_metaphlan.ipynb` | Python | Reference-based taxonomic profiling |
| `day1_lab3_mgx_visualization.ipynb` | R | Metagenomic data visualization |
| `day2_lab1_maaslin.ipynb` | R | Differential abundance with MaAsLin2 |
| `day2_lab2_metagenomic_assembly.ipynb` | Python | Metagenomic assembly |
| `day3_lab1_gene_centric_analysis.ipynb` | Python | Gene-centric analysis |
| `day3_lab2_magraph_tutorial.ipynb` | **Metabiome** | Operon abundance across cohorts |
| `day3_lab3_protein_structure.ipynb` | R | Protein structure / Foldseek |
| `day3_lab4_metabolomics.ipynb` | R | Metabolomics correlation |
| `day3_lab5_bacterial_genome_analysis.ipynb` | Python | Bacterial genome assembly and polishing |

`day3_lab2` runs on its own kernel, built by `.devcontainer/setup_metabiome.sh` during container creation — no manual step. If the kernel is missing (the warning appears in the container-create log), re-run that script; it is idempotent.

## Verifying a build (maintainers)

Before pinning a new image tag or a new data archive, run every notebook headlessly:

```bash
./scripts/run_notebooks.sh --list      # what would run, and with which kernel
./scripts/run_notebooks.sh --fast      # everything except day3_lab5 (~12 min)
./scripts/run_notebooks.sh             # the full suite (~30 min)
```

Measured on Apple Silicon, 2026-07-29: `day3_lab5` is 18 minutes of the 30 (Flye → medaka → SPAdes → polypolish → dnaapler); `day3_lab1` is 5, `day2_lab2` 2.5, and everything else is seconds.

Each notebook runs in a fresh kernel — the one it declares in its own metadata — with the repository root as the working directory, which is what a student gets in VS Code. Originals are never modified: executed copies, a per-notebook log and `summary.md` are written to `.nbrun/<timestamp>/` (gitignored). Exit status is non-zero if any notebook produced an error output.

The script works from either side of the container boundary: inside the dev container it runs directly, from the host it reuses the running dev container, or starts a throwaway one from the pinned image.

Useful flags: `--only day3_lab5` to select notebooks by substring, `-v` to stream per-cell progress, `--cell-timeout SEC` to bound a stalled cell.

> To keep a cell out of the headless run (network installs, destructive repair steps), tag it `skip-execution` in the VS Code cell tag editor. Students are unaffected — the tag only tells the runner to pass over it.

## Features

- **Python 3.10** — NumPy, Pandas, Matplotlib, Biopython
- **R 4.3** — tidyverse, ggplot2, ggpubr, vegan, reshape2, psych, compositions, MaAsLin2, with the language server pre-configured
- **Bioinformatics** — samtools, bowtie2, bwa, minimap2, BLAST, prodigal, CD-HIT, MEGAHIT, SPAdes, Foldseek, MetaPhlAn, Trim Galore, FastQC
- **Nanopore** — Flye, medaka, NanoPlot, Filtlong, lrge, dnaapler, polypolish
- **Jupyter kernels** — Python and R, both available in VS Code
- **Ubuntu 24.04** with micromamba for package management

> `prokka` and `checkm` appear in `day3_lab5` but are **not installed** — those steps use precomputed results because CheckM needs ~40 GB of RAM and Prokka does not run on ARM.

### Known differences on Apple Silicon (arm64)

The R packages `fossil` and `taxonomizr` are **not installed on arm64**. `fossil` has no arm64 build at all, and `taxonomizr`'s arm64 builds require R ≥ 4.4 while the image pins R 4.3.

The package-check cells in `day1_lab0_hello_world_r.ipynb` and `day1_lab1_test_setup_R_env.ipynb` will therefore print a "missing"/"failed to load" line for them on Apple Silicon. **This is expected, not a broken container** — no lab actually analyses anything with either package; they only appear in those checklists. Everything is present on amd64, including GitHub Codespaces.

The same cells also check `devtools`, which is not installed on any architecture.
