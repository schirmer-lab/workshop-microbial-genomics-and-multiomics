"""
I/O writer functions for saving MetabiomeDataSpace objects.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import zarr
import zarrs  # noqa: F401

from metabiome.core.matrix import SparseAbundanceMatrix
from metabiome.core.space import MetabiomeDataSpace

zarr.config.set({"codec_pipeline.path": "zarrs.ZarrsCodecPipeline"})


def write(
    space: MetabiomeDataSpace, store_path: str | Path, overwrite: bool = False
) -> None:
    """
    Save a MetabiomeDataSpace to a directory-based store.

    Args:
        space: The MetabiomeDataSpace object to save.
        store_path: Path to the output directory.
        overwrite: If True, overwrite existing directory.
    """

    path = Path(store_path) if store_path else space.outdir

    if path.exists():
        if overwrite:
            shutil.rmtree(path)
        else:
            raise FileExistsError(
                f"Store path '{path}' already exists. Use overwrite=True to replace."
            )
    path.mkdir(parents=True)

    # Write components
    _write_metadata(space, path)
    _write_abundance(space.X, path / "X")
    if space.sequences:
        _write_sequences(space, path)
    if space._id_mapping is not None:
        space._id_mapping.sink_parquet(path / "id_mapping.parquet")
    if space.uns:
        _write_uns(space.uns, path / "uns.json")


def atomic_write_store(
    write_fn,
    space: MetabiomeDataSpace,
    final_path: str | Path,
    overwrite: bool = False,
) -> None:
    """Atomically write a store by writing into a temp sibling directory then renaming.

    - write_fn(space, dest_path, overwrite=False) will be called to populate the temp dir.
    - final_path must be on the same filesystem as the temp directory to ensure atomic
      rename semantics. We place the temp directory next to the final path's parent.
    """
    final_path = Path(final_path)
    parent = final_path.parent
    parent.mkdir(parents=True, exist_ok=True)

    tmp_dir = Path(
        tempfile.mkdtemp(prefix=f".tmp-{final_path.name}-", dir=str(parent))
    )
    try:
        # Delegate writing to the existing writer but target the tmp dir.
        # Ensure write_fn does not attempt to overwrite the tmp dir itself.
        write_fn(space, tmp_dir, overwrite=False)

        # If final exists, handle overwrite semantics
        if final_path.exists():
            if not overwrite:
                raise FileExistsError(f"Store {final_path} exists")
            # Remove existing final store before replace. This introduces a brief
            # window where the final path does not exist, but is the simplest
            # cross-platform approach.
            shutil.rmtree(final_path)

        # Atomic replacement: move tmp_dir to final_path
        os.replace(str(tmp_dir), str(final_path))

    except Exception:
        # Best-effort cleanup on failure
        try:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)
        finally:
            raise


def _write_metadata(space: Any, path: Path) -> None:
    """Write obs and var LazyFrames to Parquet using sink for performance."""
    space._obs.sink_parquet(path / "obs.parquet")
    space._var.sink_parquet(path / "var.parquet")


def _write_abundance(X: SparseAbundanceMatrix, zarr_path: Path) -> None:
    """Write the SparseAbundanceMatrix to a Zarr store."""
    root = zarr.group(store=str(zarr_path), overwrite=True)

    # Store the sparse matrix components
    data_array = root.create_array(
        "data",
        shape=X.data.data.shape,
        chunks=True,
        dtype=X.data.data.dtype,
        overwrite=True,
    )
    data_array[:] = X.data.data

    indices_array = root.create_array(
        "indices",
        shape=X.data.indices.shape,
        chunks=True,
        dtype=X.data.indices.dtype,
        overwrite=True,
    )
    indices_array[:] = X.data.indices

    indptr_array = root.create_array(
        "indptr",
        shape=X.data.indptr.shape,
        chunks=True,
        dtype=X.data.indptr.dtype,
        overwrite=True,
    )
    indptr_array[:] = X.data.indptr

    # Store metadata needed to reconstruct the matrix
    root.attrs["shape"] = X.shape
    root.attrs["obs_names"] = X.obs_names
    root.attrs["var_names"] = X.var_names


def _write_sequences(space: Any, path: Path) -> None:
    """Copy the FASTA file and its index."""
    fasta_path = Path(space.sequences.filename)
    if fasta_path.exists():
        shutil.copy(fasta_path, path / "sequences.fa")
        # Also copy the index if it exists
        fai_path = Path(str(fasta_path) + ".fai")
        if fai_path.exists():
            shutil.copy(fai_path, path / "sequences.fa.fai")


def _write_uns(uns: dict, path: Path) -> None:
    """Write the unstructured metadata to a JSON file."""
    with open(path, "w") as f:
        json.dump(uns, f, indent=4)
