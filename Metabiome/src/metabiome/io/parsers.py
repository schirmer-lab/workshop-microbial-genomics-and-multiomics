"""
Structured parsers for metabiome data ingestion.

This module provides a hierarchy of parsers for different data types with
memory-efficient handling of large matrices through lazy loading and chunked storage.
"""

import json
import logging
from abc import ABC
from pathlib import Path
from typing import Dict, List, Union

import polars as pl
import pyfaidx

from ..annotations.taxonomy import ALLOWED_RANKS


class BaseParser(ABC):
    """Abstract base class for all parsers."""

    types: List[str] = []

    def __init__(self, path: Union[str, Path], **kwargs):
        """
        Initialize parser and automatically parse the file.

        Parameters
        ----------
        path : str or Path
            Path to the file to parse
        **kwargs
            Additional arguments passed to the parse method
        """
        self.path = Path(path)
        self.kwargs = kwargs
        self.is_dir = None

        self.data = self._parse()

    def _parse(self) -> Union[pl.LazyFrame, pyfaidx.Fasta]:
        """Parse a single file and return structured data."""
        self._validate()
        pass

    def _validate(self) -> bool:
        """
        Core validation logic for path existence and format support.
        """

        if not self.path.exists():
            raise FileNotFoundError(f"Path does not exist: {self.path}")

        elif self.path.is_dir():
            self.is_dir = True

            if not any(self.path.glob(f"*{ext}") for ext in self.types):
                raise ValueError(
                    f"No supported files found in directory: {self.path}. "
                    f"Supported types: {self.types}"
                )

            return True

        elif self.path.is_file():
            self.is_dir = False
            if self.path.suffix.lower() not in self.types:
                raise ValueError(
                    f"Unsupported file format: {self.path.suffix}. "
                    f"Supported types: {self.types}"
                )
            return True
        else:
            raise ValueError(f"Invalid path type: {self.path}")


class TabularParser(BaseParser):
    """Base parser for tabular data (CSV, TSV, Parquet, JSON)."""

    types = [".csv", ".tsv", ".parquet", ".json"]
    required_columns: List[str] = []

    def _validate_columns(
        self, df: pl.LazyFrame, required_columns: List[str]
    ) -> bool:
        """Validate LazyFrame has required columns."""
        return all(
            col in df.collect_schema().names() for col in required_columns
        )


class MetadataParser(TabularParser):
    """Parser for sample/feature metadata files."""

    types = [".csv", ".tsv", ".parquet"]
    required_columns = [
        "sample_id",
        "disease_group",
        "disease_state",
        "use_antibiotic",
        "age",
        "gender",
    ]

    def __init__(self, path, **kwargs):
        default = {
            "null_values": ["NA", "null", "unknown", "."],
            "ignore_errors": True,
        }

        self.kwargs = {**default, **kwargs}

        super().__init__(path, **self.kwargs)

    def _parse(self) -> pl.LazyFrame:
        """
        Parse metadata file(s) with unified API.

        Uses path type determined during validation to avoid redundant checks.

        Returns
        -------
        pl.LazyFrame
            LazyFrame with all columns cast as categorical, intersected columns for directories
        """

        super()._parse()

        if self.is_dir:
            df = self._parse_directory(**self.kwargs)
        else:
            df = self._parse_file(self.path, **self.kwargs)

        return df.with_columns(
            pl.col("disease_group").cast(pl.Categorical),
            pl.col("disease_state").cast(pl.Categorical),
            pl.col("use_antibiotic").cast(pl.Categorical),
            pl.col("gender").cast(pl.Categorical),
        ).rename(
            {
                "sample_id": "sample",
                "disease_group": "disease_group",
                "disease_state": "disease_state",
                "use_antibiotic": "use_antibiotic",
                "age": "age",
            }
        )

    def _parse_file(
        self,
        path: Path,
        **kwargs,
    ) -> pl.LazyFrame:
        """Parse a single metadata file."""
        parsers = {
            ".parquet": lambda p: pl.scan_parquet(p, **kwargs),
            ".tsv": lambda p: pl.scan_csv(p, separator="\t", **kwargs),
            ".csv": lambda p: pl.scan_csv(p, separator=";", **kwargs),
        }

        df = parsers[path.suffix.lower()](
            path,
        )

        if not self._validate_columns(df, self.required_columns):
            raise ValueError(
                f"Missing required columns in {path}. Expected: {self.required_columns}"
            )

        df = df.select(self.required_columns)

        return df

    def _parse_directory(self, **kwargs) -> pl.LazyFrame:
        """Parse all metadata files in directory and concatenate with intersected columns."""

        lazyframes: List[pl.LazyFrame] = []

        for path in sorted(self.path.glob("*")):
            try:
                df = self._parse_file(path, **kwargs)
                lazyframes.append(df)
            except Exception as e:
                logging.error(f"Failed to parse {path}: {e}")
                continue

        if not lazyframes:
            raise ValueError("No valid metadata files could be parsed")

        return pl.concat(lazyframes, how="vertical_relaxed")


class TaxonomyParser(TabularParser):
    """Parser for taxonomy annotation files."""

    types = [".json"]

    def _parse(self) -> pl.LazyFrame:
        """
        Parse taxonomy.json file to extract gene catalog IDs and taxonomic information.

        Returns
        -------
        pl.LazyFrame
            LazyFrame with columns: gc_id, msp_id, gene_category,
            gtdbtk_ann, metaphlan_LM_ann, lineage
        """
        super()._parse()

        with open(self.path, "r") as f:
            data = json.load(f)

        records: List[Dict[str, any]] = []

        for _, cohorts in data.items():
            for _, gene_entries in cohorts.items():
                for gene_catalog, taxonomy_info in gene_entries.items():
                    record = {
                        "gc_id": gene_catalog,
                        "msp_id": taxonomy_info.get("msp_id"),
                        "gene_category": taxonomy_info.get("gene_category"),
                    }

                    ranks = taxonomy_info.get("lineage", "").split("|")

                    for i, rank_name in enumerate(ALLOWED_RANKS):
                        record[rank_name] = ranks[i] if i < len(ranks) else None

                    records.append(record)

        if not records:
            raise ValueError("No taxonomy data found in file")

        df = pl.LazyFrame(records).with_columns(
            pl.col("msp_id").cast(pl.Utf8),
            pl.col("gene_category").cast(pl.Utf8),
            *[pl.col(rank).cast(pl.Utf8) for rank in ALLOWED_RANKS],
        )

        return df


class FunctionalGroupParser(TabularParser):
    """Parser for cohort functional group files."""

    types = [".json"]

    def _parse(self, explode: bool = False) -> pl.LazyFrame:
        """
        Parse FG.json file to extract gene catalog IDs and function domains.

        Returns
        -------
        pl.LazyFrame
            LazyFrame with columns: gc_id, pfam_domain.
        """

        super()._parse()

        with open(self.path, "r") as f:
            data = json.load(f)

        records: List[Dict[str, str]] = []

        for _, cohorts in data.items():
            for _, gene in cohorts.items():
                for gene_catalog, annotation in gene.items():
                    if explode:
                        for domain in annotation.split(":::"):
                            records.append(
                                {
                                    "gc_id": gene_catalog,
                                    "pfam_domain": domain.strip(),
                                }
                            )
                    else:
                        records.append(
                            {
                                "gc_id": gene_catalog,
                                "pfam_domain": annotation,
                            }
                        )

        if not records:
            raise ValueError("No functional group data found in file")

        df = pl.LazyFrame(records).with_columns(
            pl.col("pfam_domain").cast(pl.Categorical),
        )

        return df


class IDMappingParser(TabularParser):
    """Parser for ID mapping files that link gene hierarchies."""

    types = [".tsv", ".csv"]
    required_columns = [
        "gene_id",
        "gc_id",
        "cohort_name",
        "mcgc_id",  # mcgc_id is structured as cohort::::gene_id
        "mcpc_id",  # mcpc_id is structured as cohort::::gene_id
    ]

    def _parse(self, explode_ids: bool = False) -> pl.LazyFrame:
        """
        Parse ID mapping TSV file containing gene hierarchy.

        Parameters
        ----------
        explode_ids : bool, default False
            If True, parse structured mcgc_id and mcpc_id into separate components

        Returns
        -------
        pl.LazyFrame
            LazyFrame with gene ID hierarchy mapping
        """
        super()._parse()

        df = pl.scan_csv(self.path, separator="\t", **self.kwargs)

        if not self._validate_columns(df, self.required_columns):
            raise ValueError(
                f"Missing required columns. Expected: {self.required_columns}"
            )

        else:
            df = df.select(self.required_columns)

        if explode_ids:
            df = df.with_columns(
                [
                    # Extract cohort from mcgc_id (before "::::")
                    pl.col("mcgc_id")
                    .str.split("::::")
                    .list.get(0)
                    .alias("mcgc_cohort"),
                    pl.col("mcgc_id")
                    .str.split("::::")
                    .list.get(1)
                    .alias("mcgc_gene_id"),
                    # Extract cohort from mcpc_id
                    pl.col("mcpc_id")
                    .str.split("::::")
                    .list.get(0)
                    .alias("mcpc_cohort"),
                    pl.col("mcpc_id")
                    .str.split("::::")
                    .list.get(1)
                    .alias("mcpc_gene_id"),
                ]
            )

        df = df.with_columns(
            [
                pl.col("gene_id").cast(pl.Utf8),
                pl.col("gc_id").cast(pl.Utf8),
                pl.col("cohort_name").cast(pl.Utf8),
                pl.col("mcgc_id").cast(pl.Utf8),
                pl.col("mcpc_id").cast(pl.Utf8),
            ]
        )

        return df


class SequenceParser(BaseParser):
    """Parser for FASTA sequence files using pyfaidx."""

    types = [".fasta", ".fa", ".fna", ".faa"]

    def _parse(self) -> pyfaidx.Fasta:
        """
        Parse FASTA file and return pyfaidx.Fasta object for lazy loading.

        Returns
        -------
        pyfaidx.Fasta
            Indexed FASTA object for lazy sequence access
        """
        super()._parse()
        return pyfaidx.Fasta(str(self.path), **self.kwargs)


class GeneAbundanceParser(BaseParser):
    """Parser for Gene Abundance profiles with lazy loading support."""

    types = [".json"]

    def _parse(self) -> pl.LazyFrame:
        """
        Parse RPKM JSON file to long-format LazyFrame.

        Returns
        -------
        pl.LazyFrame
            Long-format LazyFrame with columns:
            - gc_id: str (Categorical)
            - sample: str (Categorical)
            - abundance: float
        """
        super()._parse()

        with open(self.path, "r") as f:
            data = json.load(f)

        records = []

        for _, cohort in data.items():
            for _, gc in cohort.items():
                for gene_catalog, abundances in gc.items():
                    for sample, abundance in abundances.items():
                        records.append(
                            {
                                "gc_id": gene_catalog,
                                "sample": sample,
                                "abundance": abundance,
                            }
                        )

        if not records:
            raise ValueError("No abundance data found in file")

        df = pl.LazyFrame(records, **self.kwargs)

        return df.with_columns(
            [
                pl.col("gc_id").cast(pl.Utf8),
                pl.col("sample").cast(pl.Utf8),
                pl.col("abundance").cast(pl.Float32),
            ]
        )
