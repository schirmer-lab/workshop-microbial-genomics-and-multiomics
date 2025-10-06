"""Backing store abstraction for MetabiomeDataSpace.

This module provides a small, high-level wrapper around the existing
readers/writers to present a single, discoverable API for saving and
loading a `MetabiomeDataSpace` to a directory-backed store (Parquet + Zarr).

The implementation here is intentionally lightweight: it delegates to the
existing io writers/readers while documenting the expected contract and
behaviour for future incremental improvements (atomic writes, versioning,
partial-recovery, etc.).
"""

from __future__ import annotations

from pathlib import Path

from ..core.space import MetabiomeDataSpace


class BackingStore:
    """High-level helper to save/load MetabiomeDataSpace objects.

    This class is intentionally thin: it centralizes the canonical save/load
    locations and provides a single place to add atomic writes, versioning,
    and migrations in the future.

    Usage (simple):
        BackingStore.save(mds, "./store")
        mds2 = BackingStore.load("./store")
    """

    @staticmethod
    def save(
        mds: MetabiomeDataSpace, store_path: str | Path, overwrite: bool = False
    ) -> None:
        """Save a `MetabiomeDataSpace` into `store_path`.

        Current behaviour: delegate to the existing writer implementation.

        Parameters
        ----------
        mds: MetabiomeDataSpace
            Data space to save.
        store_path: str | Path
            Directory path where to save the store.
        overwrite: bool
            If True, allow overwriting existing store.
        """

        from .writers import atomic_write_store, write

        # Use atomic write helper to ensure crash-safe store commits
        atomic_write_store(write, mds, Path(store_path), overwrite=overwrite)

    @staticmethod
    def load(store_path: str | Path) -> MetabiomeDataSpace:
        """Load a `MetabiomeDataSpace` from a previously saved store.

        Current behaviour: delegate to the `from_space` factory implemented
        in `io.readers` which returns a lazy-backed MetabiomeDataSpace.
        """
        from .readers import from_space

        return from_space(Path(store_path))

    @staticmethod
    def _write_atomic(temp_path: Path, final_path: Path) -> None:
        """Atomic rename helper (placeholder).

        Implement atomic move semantics and crash-safe commits here.
        """
        temp_path.rename(final_path)
