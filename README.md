# Introduction to Analysing Microbial Genomics and Multi'omics Data

> [!WARNING]
> **Setup is handled by the instructors.** For this workshop, installation, setup and initialization of the workspace are delivered to you directly at the start of the course. You don't need to do anything in this README to take part.

Course material for the workshop **"Introduction to analysing microbial genomics and multi'omics data"**, taught with a dev container providing Python, R and Jupyter with a full bioinformatics toolchain.

## Environment

The dev container can run in **GitHub Codespaces** (no local install needed) or locally in **VS Code + Docker**. See [`docs/local-setup.md`](docs/local-setup.md) for requirements, quick start, the container image, and how the course data is fetched — these steps can be followed if you'd like to work locally on your own computer instead of the environment provided during the workshop.

## Kernels

The image ships two kernels and a third is built on container create. Every notebook declares the one it needs in its own metadata:

| Kernel | Shown as | Used by |
|---|---|---|
| `ir` | **R** | all R notebooks |
| `python3` | **Python 3.10** | all Python notebooks except `MetaGEAR_vis.ipynb` |
| `metabiome` | **Python (Metabiome)** | `MetaGEAR_vis.ipynb` only — built automatically on container create |

VS Code will try to pre-select a kernel when you open the notebook; you should not have to choose. If it still shows **Select Kernel**, click it → **Jupyter Kernel...** and pick the kernel named in the table above. The R kernel is listed under "Jupyter Kernels" as plain **R**, not under a language-specific group.


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
| `R_intro_0_test_setup.ipynb` | R | Environment self-test |
| `R_intro_3_basics.ipynb` | R | Introduction to R |
| `metaphlan.ipynb` | Python | Reference-based taxonomic profiling |
| `MGX_vis.ipynb` | R | Metagenomic data visualization |
| `maaslin.ipynb` | R | Differential abundance with MaAsLin2 |
| `MGX_assembly.ipynb` | Python | Metagenomic assembly |
| `isolate_genome_analysis.ipynb` | Python | Bacterial genome assembly and polishing |
| `Gene_centric_analysis.ipynb` | Python | Gene-centric analysis |
| `MetaGEAR_vis.ipynb` | **Metabiome** | Operon abundance across cohorts |
| `protein_structure.ipynb` | R | Protein structure / Foldseek |
| `metabolomics.ipynb` | R | Metabolomics correlation |

`MetaGEAR_vis.ipynb` runs on its own kernel, built by `.devcontainer/setup_metabiome.sh` during container creation — no manual step. If the kernel is missing (the warning appears in the container-create log), re-run that script; it is idempotent.

## Features

- **Python 3.10** — NumPy, Pandas, Matplotlib, Biopython
- **R 4.3** — tidyverse, ggplot2, ggpubr, vegan, reshape2, psych, compositions, MaAsLin2, with the language server pre-configured
- **Bioinformatics** — samtools, bowtie2, bwa, minimap2, BLAST, prodigal, CD-HIT, MEGAHIT, SPAdes, Foldseek, MetaPhlAn, Trim Galore, FastQC
- **Nanopore** — Flye, medaka, NanoPlot, Filtlong, lrge, dnaapler, polypolish
- **Jupyter kernels** — Python and R, both available in VS Code
- **Ubuntu 24.04** with micromamba for package management

### Known differences on Apple Silicon (arm64)

The R package `fossil` is **not installed on arm64** — it has no arm64 build at all.

The package-check cells in `R_intro_0_test_setup.ipynb` will therefore print a "missing"/"failed to load" line for it on Apple Silicon. **This is expected, not a broken container**.
