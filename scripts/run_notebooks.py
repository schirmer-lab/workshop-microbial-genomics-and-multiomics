#!/usr/bin/env python3
# =============================================================================
# Execute every workshop notebook headlessly and report which cells fail.
#
#   ./scripts/run_notebooks.sh                 # everything (~30 min)
#   ./scripts/run_notebooks.sh --fast          # skip day3_lab5 (~12 min)
#   ./scripts/run_notebooks.sh --only day1     # substring filter
#   ./scripts/run_notebooks.sh --list          # show what would run
#
# Runs each notebook with its OWN declared kernel (metadata.kernelspec.name), in
# a fresh kernel, with the repository root as the working directory -- the same
# conditions a student gets in VS Code. Originals are never modified: executed
# copies, per-notebook logs and a summary are written to the output directory.
#
# Cells tagged `skip-execution` are not run. Use that tag for anything that must
# not run unattended (network installs, destructive fixes); it is the standard
# nbclient/nbconvert tag and VS Code shows it in the cell tag editor.
#
# Exit status is 0 only if every selected notebook finished with no error output.
# =============================================================================

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# What --fast skips. Measured on Apple Silicon, 2026-07-29: the whole suite is
# ~30 min and day3_lab5 alone is 18 of them. Everything else is seconds to a few
# minutes (day3_lab1 297s and day2_lab2 146s are the next largest), so there is
# nothing else worth dropping.
HEAVY = {
    "day3_lab5_bacterial_genome_analysis.ipynb": "runs Flye, SPAdes, medaka, polypolish (~18 min)",
}

# Kernels that are not in the image itself.
EXTRA_KERNEL_HINT = {
    "metabiome": "postCreateCommand should have built it; re-run .devcontainer/setup_metabiome.sh",
}

C_OK, C_BAD, C_WARN, C_DIM, C_OFF = "\033[0;32m", "\033[0;31m", "\033[1;33m", "\033[2m", "\033[0m"


def color(txt: str, c: str, enabled: bool) -> str:
    return f"{c}{txt}{C_OFF}" if enabled else txt


def discover(only: list[str] | None) -> list[Path]:
    nbs = sorted(p for p in REPO.glob("day*.ipynb"))
    if only:
        nbs = [p for p in nbs if any(o in p.name for o in only)]
    return nbs


def installed_kernels() -> dict[str, str]:
    from jupyter_client.kernelspec import KernelSpecManager

    return KernelSpecManager().find_kernel_specs()


def declared_kernel(nb_path: Path) -> tuple[str, str]:
    """(kernel name, language) as declared in the notebook metadata."""
    meta = json.loads(nb_path.read_text())["metadata"]
    ks = meta.get("kernelspec", {})
    return ks.get("name", ""), ks.get("language", meta.get("language_info", {}).get("name", ""))


def error_cells(nb) -> list[dict]:
    """Cells that produced an error output, in notebook order."""
    out = []
    for i, cell in enumerate(nb.cells):
        for o in cell.get("outputs", []):
            if o.get("output_type") == "error":
                out.append(
                    {
                        "cell": i,
                        "ename": o.get("ename", "?"),
                        "evalue": (o.get("evalue", "") or "").strip().splitlines()[:1],
                        "source": "".join(cell["source"])[:400],
                    }
                )
                break
    return out


def git_state() -> set[str]:
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=REPO, capture_output=True, text=True, timeout=60,
        )
        return set(r.stdout.splitlines())
    except Exception:
        return set()


def run_one(nb_path: Path, kernel: str, cell_timeout: int, outdir: Path, verbose: bool) -> dict:
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import CellTimeoutError

    nb = nbformat.read(nb_path, as_version=4)
    n_code = sum(1 for c in nb.cells if c.cell_type == "code")
    logf = (outdir / f"{nb_path.stem}.log").open("w")
    started = {}

    def note(msg: str) -> None:
        logf.write(msg + "\n")
        logf.flush()
        if verbose:
            print(f"    {msg}", flush=True)

    def on_cell_start(cell=None, cell_index=None, **_):
        started[cell_index] = time.monotonic()
        first = "".join(cell["source"]).strip().splitlines()[:1]
        note(f"[{datetime.now():%H:%M:%S}] cell {cell_index} -> {first[0][:90] if first else ''}")

    def on_cell_executed(cell=None, cell_index=None, **_):
        dt = time.monotonic() - started.get(cell_index, time.monotonic())
        if dt > 5:
            note(f"           cell {cell_index} took {dt:.0f}s")

    client = NotebookClient(
        nb,
        timeout=cell_timeout,
        kernel_name=kernel,
        allow_errors=True,          # collect every failure, do not stop at the first
        interrupt_on_timeout=False,  # a stalled cell aborts this notebook, not the suite
        record_timing=True,
        skip_cells_with_tag="skip-execution",
        resources={"metadata": {"path": str(REPO)}},
        on_cell_start=on_cell_start,
        on_cell_executed=on_cell_executed,
    )

    t0 = time.monotonic()
    status, detail = "ok", ""
    try:
        client.execute()
    except CellTimeoutError as exc:
        status, detail = "timeout", f"no reply within {cell_timeout}s"
        note(f"TIMEOUT: {exc}")
    except Exception as exc:  # kernel died, missing kernel binary, ...
        status, detail = "aborted", f"{type(exc).__name__}: {exc}"
        note(f"ABORTED: {detail}")
    duration = time.monotonic() - t0

    nbformat.write(nb, outdir / nb_path.name)
    errs = error_cells(nb)
    if errs and status == "ok":
        status = "errors"
    logf.close()

    return {
        "notebook": nb_path.name,
        "kernel": kernel,
        "status": status,
        "detail": detail,
        "seconds": round(duration, 1),
        "code_cells": n_code,
        "errors": errs,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Execute the workshop notebooks headlessly.")
    ap.add_argument("--only", action="append", metavar="SUBSTR",
                    help="only notebooks whose filename contains SUBSTR (repeatable)")
    ap.add_argument("--fast", "--quick", dest="fast", action="store_true",
                    help="skip the long-running notebooks (see HEAVY); --quick is an alias")
    ap.add_argument("--cell-timeout", type=int, default=3600, metavar="SEC",
                    help="abort a notebook if one cell produces no reply for SEC (default 3600)")
    ap.add_argument("--out", type=Path, default=None, metavar="DIR",
                    help="output directory (default .nbrun/<timestamp>)")
    ap.add_argument("--list", action="store_true", help="show the selection and exit")
    ap.add_argument("-v", "--verbose", action="store_true", help="stream per-cell progress")
    args = ap.parse_args()

    tty = sys.stdout.isatty()
    nbs = discover(args.only)
    if not nbs:
        print("No notebooks matched.", file=sys.stderr)
        return 2

    kernels = installed_kernels()
    plan = []
    for p in nbs:
        kern, lang = declared_kernel(p)
        if args.fast and p.name in HEAVY:
            plan.append((p, kern, "skipped", f"--fast: {HEAVY[p.name]}"))
        elif not kern:
            plan.append((p, kern, "skipped", "no kernelspec in notebook metadata"))
        elif kern not in kernels:
            hint = EXTRA_KERNEL_HINT.get(kern, "kernel not installed in this container")
            plan.append((p, kern, "skipped", f"kernel '{kern}' unavailable -- {hint}"))
        else:
            plan.append((p, kern, "run", lang))

    if args.list:
        print(f"{'notebook':<48} {'kernel':<10} action")
        for p, kern, action, why in plan:
            mark = color("run", C_OK, tty) if action == "run" else color("skip", C_WARN, tty)
            print(f"{p.name:<48} {kern:<10} {mark}  {C_DIM if tty else ''}{why}{C_OFF if tty else ''}")
        print(f"\nkernels available here: {', '.join(sorted(kernels)) or '(none)'}")
        return 0

    stamp = datetime.now().strftime("%y%m%d_%H%M%S")
    outdir = args.out or (REPO / ".nbrun" / stamp)
    outdir.mkdir(parents=True, exist_ok=True)

    to_run = [x for x in plan if x[2] == "run"]
    print(f"Output directory: {outdir}")
    print(f"Running {len(to_run)} of {len(plan)} notebook(s), cell timeout {args.cell_timeout}s.\n")

    before = git_state()
    results = []
    for p, kern, action, why in plan:
        if action != "run":
            print(f"  {color('SKIP', C_WARN, tty)}  {p.name:<48} {why}")
            results.append({"notebook": p.name, "kernel": kern, "status": "skipped",
                            "detail": why, "seconds": 0, "code_cells": 0, "errors": []})
            continue
        print(f"  ....  {p.name:<48} [{kern}]", end="\r" if not args.verbose else "\n", flush=True)
        res = run_one(p, kern, args.cell_timeout, outdir, args.verbose)
        results.append(res)
        tag = {"ok": (" OK ", C_OK), "errors": ("FAIL", C_BAD),
               "timeout": ("TIME", C_BAD), "aborted": ("DEAD", C_BAD)}[res["status"]]
        extra = res["detail"] or (f"{len(res['errors'])} failing cell(s): "
                                  + ", ".join(str(e["cell"]) for e in res["errors"]) if res["errors"] else "")
        print(f"  {color(tag[0], tag[1], tty)}  {p.name:<48} {res['seconds']:>7.0f}s  {extra}")
    after = git_state()

    stray = sorted(after - before)
    ok = all(r["status"] in ("ok", "skipped") for r in results)

    # ---- report ------------------------------------------------------------
    lines = [f"# Notebook run {stamp}", "",
             f"- cell timeout: {args.cell_timeout}s",
             f"- kernels available: {', '.join(sorted(kernels))}", "",
             "| Notebook | Kernel | Status | Time | Notes |", "|---|---|---|---:|---|"]
    for r in results:
        note = r["detail"] or (", ".join(f"cell {e['cell']}: {e['ename']}" for e in r["errors"]))
        lines.append(f"| `{r['notebook']}` | {r['kernel']} | {r['status']} | {r['seconds']:.0f}s | {note} |")
    for r in results:
        if not r["errors"]:
            continue
        lines += ["", f"## {r['notebook']}", ""]
        for e in r["errors"]:
            val = e["evalue"][0] if e["evalue"] else ""
            lines += [f"**cell {e['cell']} — {e['ename']}**: {val}", "", "```", e["source"], "```", ""]
    if stray:
        lines += ["", "## Files the run left in the working tree", ""] + [f"- `{s}`" for s in stray]

    (outdir / "summary.md").write_text("\n".join(lines) + "\n")
    (outdir / "summary.json").write_text(json.dumps(results, indent=2) + "\n")

    print()
    if stray:
        print(color(f"Note: the run changed {len(stray)} path(s) in the working tree:", C_WARN, tty))
        for s in stray[:10]:
            print(f"  {s}")
        if len(stray) > 10:
            print(f"  ... and {len(stray) - 10} more")
    print(f"\nSummary: {outdir / 'summary.md'}")
    print(color("All selected notebooks passed." if ok else "Some notebooks failed -- see the summary.",
                C_OK if ok else C_BAD, tty))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
