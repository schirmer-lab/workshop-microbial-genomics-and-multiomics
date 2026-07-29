# Platform support

Which platforms the workshop environment runs on, what differs between them, and which notebooks are affected.

*Last verified: 2026-07-29, against the `multiomics26` image definition.*

## The split is CPU architecture, not operating system

This is the thing to get right before worrying about Windows: the multi-architecture image is built for **`linux/amd64`** and **`linux/arm64`**. Every student runs a *Linux* container regardless of their host OS. Windows and macOS only decide which of the two they get.

| How the student runs it | Container architecture | Package set |
|---|---|---|
| **GitHub Codespaces** (browser or VS Code, any host OS) | `linux/amd64` | **full** |
| Windows + Docker Desktop (WSL2 backend) | `linux/amd64` | **full** |
| Linux x86_64 + Docker | `linux/amd64` | **full** |
| Intel Mac + Docker Desktop | `linux/amd64` | **full** |
| Apple Silicon Mac + Docker Desktop | `linux/arm64` | full **minus 2 R packages** |

**A Windows-heavy room is the best case, not the worst.** Windows PCs are x86_64, so they get `linux/amd64` — the complete package set with nothing missing. Codespaces also always runs `linux/amd64` no matter what the student's laptop is.

The only degraded platform is **Apple Silicon Macs** (likely instructors and a handful of students), and the gap is two R packages that no lab analyses anything with.

## What is missing on arm64, and where it shows

| Package | Why it is missing on arm64 |
|---|---|
| `r-fossil` | No `linux-aarch64` build exists on conda-forge at all. |
| `r-taxonomizr` | Has `linux-aarch64` builds, but only against `r-base >= 4.4`. The image pins `r-base 4.3`. |

Everything else in `environment.yml` installs on both architectures — confirmed by a full dependency solve on each (669 packages on arm64, 677 on amd64).

### Notebooks affected on Apple Silicon

Both are **environment self-checks that print a status line**. Neither computes anything with the missing package, so no exercise result changes.

| Notebook | Where | Effect on arm64 |
|---|---|---|
| `day1_lab0_hello_world_r.ipynb` | cell 4, `packages_to_test` | prints `✗ taxonomizr failed to load` |
| `day1_lab1_test_setup_R_env.ipynb` | cells 3 and 5, `required_packages` / `libraries_to_test` | prints `❌ fossil is missing` / `❌ Error loading fossil` |

The packages actually used for analysis across all labs are `ggplot2`, `tidyverse`, `vegan`, `ggpubr`, `reshape2`, `psych`, `compositions`, `Maaslin2` and `stringr` — all present on both architectures.

### Not architecture-related, but shows up in the same checklists

- `devtools` is checked in `day1_lab0` cell 4 but is **not installed on any architecture**. It prints `✗` for everyone. Confirmed absent in the built image.
- `prokka` (`day3_lab5` cell 61) — already commented out; the notebook's own comment says "does not run on ARM architecture". Uses precomputed results, so it affects nobody at runtime.
- `checkm` (`day3_lab5` cell 56) — already commented out; needs ~40 GB RAM, not an architecture issue. Uses precomputed results.

### Runtime verification (done)

The arm64 solve only proves everything *installs*. Runtime behaviour was checked separately with `./scripts/run_notebooks.sh` (see the README), which executes every notebook end to end and writes a per-cell failure report.

**All 12 notebooks pass on Apple Silicon (`linux/arm64`), 2026-07-29.** That includes the notebook that does the most real computation, `day3_lab5` — `filtlong`, `lrge`, `flye`, `medaka`, `trim_galore`, `fastqc`, `spades`, `bwa`, `polypolish`, `dnaapler`, `minimap2`, `NanoPlot` — in 18 minutes, plus `day2_lab2` (MEGAHIT, 2.5 min), `day3_lab1` (prodigal, cd-hit, bowtie2, 5 min), `day3_lab3` (Foldseek) and `day2_lab1` (MaAsLin2). Nothing in the toolchain misbehaves on arm64.

The run also confirmed the table above at runtime rather than by dependency solve: `day1_lab0` printed `✗ taxonomizr failed to load` and `day1_lab1_test_setup_R_env` printed `❌ fossil is missing`. Those two lines are the *entire* observable arm64 difference.

On `linux/amd64`, `day2_lab1` (MaAsLin2) was spot-checked on an Intel Mac. The rest of amd64 is covered by the image build's own `test_environment.sh`; a full `run_notebooks.sh` pass on an amd64 machine or in a Codespace is still the cleanest way to close it out.

## Delivering in DGL11

[Room page](https://www.ls.tum.de/it/it-raeume/dgl11/) — 30 workstations:

- 25× Dell Precision 3460 — i7-14700, **32 GB RAM**
- 5× Fujitsu ESPRIMO D538/E — i7-8700, **16 GB RAM**

All Intel x86_64, so all `linux/amd64` and the full package set either way.

**The room's OS is not published.** The LSIT pages state only that lab software is adjusted per semester on request via the room booking — which is also the channel for asking the questions below.

### Recommended route: Codespaces in the browser

Independent of what the room PCs run, and it avoids three problems at once:

1. **No admin rights needed.** Docker Desktop on Windows requires installing WSL2/Hyper-V and admin privileges, which a managed university pool almost certainly does not grant students.
2. **No network stampede.** Running locally means 30 machines each pulling a ~3 GB image plus ~2 GB of data — roughly 150 GB over the room uplink, simultaneously, at the start of the session. With Codespaces those downloads happen inside Azure and never touch the room's network.
3. **No local disk pressure**, and the 5 older 16 GB machines are not asked to run SPAdes with `--memory 16`.

Codespaces machines are configured via `hostRequirements` in `devcontainer.json` (currently 4 cores / 16 GB). Students on the [GitHub Student Developer Pack](github-edu-info.md) get 180 core-hours per month.

### Questions to put to LSIT when booking

1. What OS do the DGL11 machines run — Windows only, or is a Linux boot available?
2. Do student accounts have local administrator rights?
3. Is Docker Desktop (or Docker Engine under a Linux boot) available or installable?
4. Is WSL2 enabled on the Windows image?
5. What is the room's internet bandwidth, and is there per-machine disk quota?

Answers to 2–4 decide whether local Docker is viable at all; the answer to 5 decides whether it is *advisable* even if viable.

### Fallback if Codespaces is not usable

If browser access to GitHub Codespaces is blocked, the local Docker route on Windows needs, per machine: admin rights, WSL2, ~15 GB free disk, and a pre-seeded `~/biodata` so the 2 GB archive is not downloaded 30 times. Pre-staging both the image (`docker load` from a USB/network share) and the extracted `biodata` directory ahead of the session is strongly advised.
