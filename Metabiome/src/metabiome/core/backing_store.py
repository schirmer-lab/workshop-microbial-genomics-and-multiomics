"""
Backing store abstraction for disk-backed operations in MetabiomeDataSpace.

Provides unified interface for different storage backends (Zarr v3, Parquet)
with lazy loading and efficient partial access patterns.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Union

import polars as pl
import zarr


class BackingStore(ABC):
    """
    Abstract base class for backing store implementations.

    Defines interface for disk-backed data storage and retrieval
    with lazy loading capabilities.
    """

    @abstractmethod
    def read_samples(self) -> pl.LazyFrame:
        """Read sample metadata."""
        pass

    @abstractmethod
    def read_abundance(
        self,
        sample_ids: Optional[List[str]] = None,
        feature_ids: Optional[List[str]] = None,
    ) -> pl.LazyFrame:
        """Read abundance data with optional subsetting."""
        pass

    @abstractmethod
    def read_annotation(self, annotation_type: str) -> pl.LazyFrame:
        """Read annotation data by type."""
        pass

    @abstractmethod
    def write_samples(self, data: pl.LazyFrame) -> None:
        """Write sample metadata."""
        pass

    @abstractmethod
    def write_abundance(self, data: pl.LazyFrame) -> None:
        """Write abundance data."""
        pass

    @abstractmethod
    def write_annotation(
        self, annotation_type: str, data: pl.LazyFrame
    ) -> None:
        """Write annotation data."""
        pass


class ParquetBackingStore(BackingStore):
    """
    Parquet-based backing store for tabular data.

    Optimized for metadata and annotation storage with efficient
    columnar access patterns.
    """

    def __init__(self, base_path: Union[str, Path]):
        """
        Initialize Parquet backing store.

        Parameters
        ----------
        base_path : str or Path
            Base directory for Parquet files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def read_samples(self) -> pl.LazyFrame:
        """Read sample metadata from Parquet."""
        samples_path = self.base_path / "samples.parquet"
        if samples_path.exists():
            return pl.scan_parquet(samples_path)
        else:
            raise FileNotFoundError(f"Samples file not found: {samples_path}")

    def read_abundance(
        self,
        sample_ids: Optional[List[str]] = None,
        feature_ids: Optional[List[str]] = None,
    ) -> pl.LazyFrame:
        """Read abundance data with optional filtering."""
        abundance_path = self.base_path / "abundance.parquet"
        if not abundance_path.exists():
            raise FileNotFoundError(
                f"Abundance file not found: {abundance_path}"
            )

        # Start with lazy scan
        df = pl.scan_parquet(abundance_path)

        # Apply filters if provided
        if sample_ids is not None:
            df = df.filter(pl.col("sample").is_in(sample_ids))
        if feature_ids is not None:
            df = df.filter(pl.col("gc_id").is_in(feature_ids))

        return df

    def read_annotation(self, annotation_type: str) -> pl.LazyFrame:
        """Read annotation data by type."""
        annotation_path = self.base_path / f"{annotation_type}.parquet"
        if annotation_path.exists():
            return pl.scan_parquet(annotation_path)
        else:
            raise FileNotFoundError(
                f"Annotation file not found: {annotation_path}"
            )

    def write_samples(self, data: pl.LazyFrame) -> None:
        """Write sample metadata to Parquet."""
        samples_path = self.base_path / "samples.parquet"
        data.collect().write_parquet(samples_path)

    def write_abundance(self, data: pl.LazyFrame) -> None:
        """Write abundance data to Parquet."""
        abundance_path = self.base_path / "abundance.parquet"
        data.collect().write_parquet(abundance_path)

    def write_annotation(
        self, annotation_type: str, data: pl.LazyFrame
    ) -> None:
        """Write annotation data to Parquet."""
        annotation_path = self.base_path / f"{annotation_type}.parquet"
        data.collect().write_parquet(annotation_path)


class ZarrBackingStore(BackingStore):
    """
    Zarr v3-based backing store for array data.

    Optimized for large numerical arrays with chunking and compression.
    Particularly useful for dense abundance matrices.
    """

    def __init__(self, store_path: Union[str, Path]):
        """
        Initialize Zarr backing store.

        Parameters
        ----------
        store_path : str or Path
            Path to Zarr store
        """
        self.store_path = Path(store_path)
        self.store = zarr.open(str(self.store_path), mode="a")


class HybridBackingStore(BackingStore):
    """
    Hybrid backing store using optimal storage for each data type.

    - Parquet for metadata and annotations (columnar access)
    - Zarr for large numerical arrays (chunked access)
    """

    def __init__(self, base_path: Union[str, Path]):
        """
        Initialize hybrid backing store.

        Parameters
        ----------
        base_path : str or Path
            Base directory for data storage
        """
        self.base_path = Path(base_path)
        self.parquet_store = ParquetBackingStore(self.base_path / "metadata")
        self.zarr_store = ZarrBackingStore(self.base_path / "arrays")

    def read_samples(self) -> pl.LazyFrame:
        """Read sample metadata from Parquet."""
        return self.parquet_store.read_samples()

    def read_abundance(
        self,
        sample_ids: Optional[List[str]] = None,
        feature_ids: Optional[List[str]] = None,
    ) -> pl.LazyFrame:
        """Read abundance data, preferring Parquet for flexibility."""
        return self.parquet_store.read_abundance(sample_ids, feature_ids)

    def read_annotation(self, annotation_type: str) -> pl.LazyFrame:
        """Read annotation data from Parquet."""
        return self.parquet_store.read_annotation(annotation_type)

    def write_samples(self, data: pl.LazyFrame) -> None:
        """Write sample metadata to Parquet."""
        self.parquet_store.write_samples(data)

    def write_abundance(self, data: pl.LazyFrame) -> None:
        """Write abundance data to Parquet."""
        self.parquet_store.write_abundance(data)

    def write_annotation(
        self, annotation_type: str, data: pl.LazyFrame
    ) -> None:
        """Write annotation data to Parquet."""
        self.parquet_store.write_annotation(annotation_type, data)
