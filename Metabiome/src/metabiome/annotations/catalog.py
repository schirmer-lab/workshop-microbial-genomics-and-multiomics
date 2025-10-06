import abc
import asyncio
import io
import logging
import os
import threading
from typing import TYPE_CHECKING, Generator, Iterable, Literal

import aiofiles
import numpy as np
import polars as pl
from joblib import Parallel, delayed
from pyfamsa import Aligner, Alignment, Sequence

from ..utils._helpers import setup_logging, timer

if TYPE_CHECKING:
    from metabiome.core.space import MetabiomeDataSpace


try:
    from ..optimized import (
        calculate_average_pid,
        calculate_positional_pid,
        classify_mutations,
        codon_to_aa,
        get_most_common_base,
        protein_to_nucleotide,
    )

except ImportError:

    def calculate_average_pid(*args, **kwargs):
        raise ImportError(
            "Optimized functions not available. Build with: uv run python setup.py build_ext --inplace"
        )

    def calculate_positional_pid(*args, **kwargs):
        raise ImportError(
            "Optimized functions not available. Build with: uv run python setup.py build_ext --inplace"
        )

    def classify_mutations(*args, **kwargs):
        raise ImportError(
            "Optimized functions not available. Build with: uv run python setup.py build_ext --inplace"
        )

    def codon_to_aa(*args, **kwargs):
        raise ImportError(
            "Optimized functions not available. Build with: uv run python setup.py build_ext --inplace"
        )

    def get_most_common_base(*args, **kwargs):
        raise ImportError(
            "Optimized functions not available. Build with: uv run python setup.py build_ext --inplace"
        )

    def protein_to_nucleotide(*args, **kwargs):
        raise ImportError(
            "Optimized functions not available. Build with: uv run python setup.py build_ext --inplace"
        )


class GroupAccessor:
    """Baseclass for annotating grouped sequences, creating alignments, and identifying mutations."""

    def __init__(
        self,
        mds: "MetabiomeDataSpace",
    ):
        """
        Initialize the sequence annotation with input and output paths.

        Parameters
        ----------
        mds : MetabiomeDataSpace
            MetabiomeDataSpace object
        """
        self._mds = mds

        self._mapping: dict[str, np.ndarray] = {}
        self._alignment: dict[str, Alignment | None] = {}
        self._consensus: bytes | None = None
        self._mutations: pl.DataFrame | None = None
        self._positional_pid: np.ndarray | None = None

    def __call__(self, *args, **kwargs):
        pass

    @timer()
    def generate_consensus(
        self,
        key: str,
        threshold: float = 0.1,
        include_gaps: bool = True,
    ) -> None:
        """
        Generate a consensus sequence from a multiple sequence alignment using NumPy.

        Parameters
        ----------
        key : str, optional
            Key to the alignment dictionary (e.g., "protein", "nucleotide").
            Defaults to "nucleotide".
        threshold : float, optional
            Minimum frequency threshold for a base to be considered part of the
            consensus. Defaults to 0.1.
        include_gaps : bool, optional
            Whether to include gaps ('-') when calculating the consensus. Defaults to True.
        """
        assert key in self.alignment, (
            f"{key} alignment not found. Run get_nucleotide_alignment() first."
        )

        matrix = np.array(
            [
                np.frombuffer(record.sequence, dtype="S1")
                for record in self.alignment[key] or []
            ],
            dtype="S1",
        )

        with Parallel(n_jobs=self.n_jobs) as parallel:
            consensus = parallel(
                delayed(get_most_common_base)(
                    matrix[:, i], threshold, include_gaps
                )
                for i in range(matrix.shape[1])
            )

        self.consensus = bytes(consensus)

    @timer()
    def translate_sequence(
        self,
        table: int = 11,
    ) -> list[Sequence]:
        """
        Translate nucleotide sequences to protein sequences and store the amino acid index to codon mapping.

        Parameters
        ----------
        table : int, optional
            Codon table to use for translation. Defaults to 11.

        Returns
        -------
        list[Sequence]
            List of translated protein sequences.
        """

        with Parallel(n_jobs=self.n_jobs) as parallel:
            result = parallel(
                delayed(codon_to_aa)(name, seq, table) for name, seq in self
            )

        translated = []

        for name, aa, aa_to_codon in result:
            translated.append(
                Sequence(
                    id=name,
                    sequence=aa,
                )
            )

            self.mapping[name] = aa_to_codon

        return translated

    @timer()
    def align_prot_seq(
        self,
        threads: int,
        sequences: Iterable[Sequence],
    ) -> None:
        """
        Align protein sequences using FAMSA.

        Parameters
        ----------
        threads : int
            The number of threads to use for the alignment process.
        sequences : Iterable[Sequence]
            An iterable containing the protein sequences to be aligned.
        """
        alignment: Alignment = Aligner(
            threads=threads, guide_tree="upgma"
        ).align(sequences)

        self.alignment["protein"] = alignment

    async def _save_alignment(self) -> None:
        """
        Asynchronously save the alignment to a file.
        """
        for name, alignment in self.alignment.items():
            async with aiofiles.open(
                self._mds.outdir / f"{name}.aln", "w"
            ) as f:
                await f.write(
                    "\n".join(
                        f">{seq.id.decode()}\n{seq.sequence.decode()}"
                        for seq in alignment
                    )
                )

    def __getitem__(self, item: str) -> Sequence:
        """
        Retrieve a sequence from the catalog by its identifier.

        Parameters
        ----------
        item : str
            The identifier of the sequence to retrieve.

        Returns
        -------
        Sequence
            The Sequence object corresponding to the given identifier.

        Raises
        ------
        KeyError
            If the sequence with the specified identifier is not found in the catalog.
        """
        try:
            seq = self._mds.sequences[item]
        except KeyError:
            raise KeyError(f"Sequence '{item}' not found in catalog.")
        return Sequence(
            id=item.encode(),
            sequence=str(seq).encode(),
        )

    def __iter__(self) -> Generator[tuple[bytes, bytes], None, None]:
        """
        Iterate over the sequences in the catalog, yielding both the sequence ID and sequence as bytes.

        Yields
        -------
        tuple[bytes, bytes]
            A tuple containing the sequence ID (as bytes) and the sequence (as bytes).
        """
        for name in self._mds.var_names:
            try:
                rec = self._mds.sequences[name]

            except KeyError:
                logging.warning(
                    f"Sequence '{name}' not found in catalog, skipping."
                )
                continue
            yield str(name).encode("utf-8"), str(rec).encode("utf-8")

        return

    def __len__(self) -> int:
        """
        Get the number of sequences in the catalog.
        """
        count = 0

        for name in self._mds.var_names:
            if name in self._mds.sequences:
                count += 1

        return count

    def __contains__(self, item: str) -> bool:
        """
        Check if a sequence ID exists in the catalog.
        """
        return item in self._mds.var_names and item in self._mds.sequences

    def __str__(self) -> str:
        """
        String representation of the SequenceCatalog.
        """
        return f"SequenceCatalog(type={self.sequence_type}, length={len(self)})"

    def __repr__(self) -> str:
        """
        String representation of the SequenceCatalog.
        """
        return self.__str__()

    @property
    def mapping(self):
        return self._mapping

    @mapping.setter
    def mapping(self, value: dict):
        self._mapping = value

    @property
    def alignment(self):
        return self._alignment

    @alignment.setter
    def alignment(self, value: dict[str, Alignment | None]):
        self._alignment = value

    @property
    def consensus(self):
        return self._consensus

    @consensus.setter
    def consensus(self, value: bytes):
        self._consensus = value

    @property
    def mutations(self):
        return self._mutations

    @mutations.setter
    def mutations(self, value: pl.DataFrame):
        self._mutations = value

    @property
    @abc.abstractmethod
    def sequence_type(self) -> str:
        """Abstract property: Must be implemented by subclasses (e.g., 'nucleotide', 'protein')."""
        raise NotImplementedError(
            "Subclasses must implement sequence_type property."
        )


class GeneGroup(GroupAccessor):
    """
    Represents a Metagenomic Gene Group (group-level operations on gene catalog).
    This class performs translation, protein alignment, nucleotide alignment,
    consensus generation, and mutation annotation for gene sets.
    """

    def __call__(
        self,
        threads: int | None = None,
        threshold: float = 0.1,
        format: Literal["csv", "tsv", "json"] = "csv",
        persist: bool = False,
        verbose: bool = False,
    ) -> pl.DataFrame:
        """Run the full annotation pipeline and return mutations as a Polars DataFrame.

        Parameters
        ----------
        threads : int | None
            Number of threads to use for protein alignment. Defaults to os.cpu_count().
        threshold : float
            Consensus frequency threshold.
        format : {'csv','tsv','json'}
            Format used when persisting mutation table.
        persist : bool
            If True, write consensus and mutations to disk using existing async helpers.

        Returns
        -------
        pl.DataFrame
            Aggregated mutations table as a Polars DataFrame, including count, percentage (PID), position_bp, and group_pid.
        """
        setup_logging(verbosity=verbose)

        self.n_jobs = threads if threads else os.cpu_count()

        self.align_prot_seq(
            threads=self.n_jobs,
            sequences=self.translate_sequence(),
        )
        self.get_nucleotide_alignment()
        self.generate_consensus(threshold=threshold, key="nucleotide")
        self.annotate_mutations()

        self.mutations = pl.read_csv(io.StringIO(self.mutations))

        total_seqs = len(self.alignment.get("nucleotide", []))
        self.mutations = (
            self.mutations.group_by(
                ["position", "mutation", "ref_aa", "var_aa"]
            )
            .count()
            .with_columns(
                (pl.col("count") / total_seqs * 100).alias("percentage"),
                (pl.col("position") * 3).alias("position_bp"),
            )
            .sort("position")
        )

        if "nucleotide" in self.alignment and self.alignment["nucleotide"]:
            matrix = np.stack(
                [
                    np.frombuffer(record.sequence, dtype=np.int8)
                    for record in self.alignment["nucleotide"]
                ]
            )
            assert matrix.shape[1] == len(self.consensus), (
                f"Matrix shape {matrix.shape} does not match consensus length {len(self.consensus)}"
            )
            group_pid = calculate_average_pid(
                matrix,
                np.frombuffer(self.consensus, dtype=np.int8).copy(),
            )
            self.mutations = self.mutations.with_columns(
                pl.lit(group_pid).alias("group_pid")
            )
            self._positional_pid = calculate_positional_pid(
                matrix,
                np.frombuffer(self.consensus, dtype=np.int8).copy(),
            )

        if persist:

            async def run_io():
                await asyncio.gather(
                    self._save_alignment(),
                    self._save_annotations(format=format),
                )

            def run_in_thread():
                asyncio.run(run_io())

            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()

        return self.mutations

    @timer()
    def get_nucleotide_alignment(self) -> None:
        """
        Get nucleotide alignment from the protein alignment.
        """
        assert "protein" in self.alignment, (
            "Protein alignment not found. Run align_prot_seq() first."
        )

        with Parallel(n_jobs=1) as parallel:
            results = parallel(
                delayed(protein_to_nucleotide)(
                    seq.id, seq.sequence, self.mapping[seq.id]
                )
                for seq in self.alignment["protein"] or []
            )

        self._alignment["nucleotide"] = Alignment(results)

    @timer()
    def annotate_mutations(self) -> None:
        """
        Annotates mutations compared to the consensus sequence for all aligned sequences
        using Cython-accelerated logic and parallel processing, writing to in-memory buffers.
        """
        assert self.consensus, (
            "Consensus sequence not found. Run generate_consensus() first."
        )

        def annotate(record, consensus):
            buf = io.StringIO()
            classify_mutations(
                record.id,
                record.sequence,
                consensus,
                11,
                buf,
            )
            return buf.getvalue()

        with Parallel(n_jobs=self.n_jobs) as parallel:
            results = parallel(
                delayed(annotate)(record, self.consensus)
                for record in self.alignment["nucleotide"] or []
            )

        self.mutations = (
            "identifier,position,ref_aa,var_aa,mutation\n" + "".join(results)
        )

    async def _save_annotations(self, format: str = "csv") -> bool:
        """
        Helper method to save mutation annotations to file

        Parameters
        ----------
        format: Format to save the mutations in (e.g., "csv", "tsv", "json")

        Returns
        -------
            bool: True if successful, False otherwise
        """

        if self.mutations is None:
            raise RuntimeError(
                "Mutations not found. Run annotate_mutations() first."
            )

        async with aiofiles.open(
            self._mds.outdir / "consensus.fasta", "wb"
        ) as f:
            await f.write(self.consensus)

        out = self._mds.outdir / f"mutations.{format}"

        if isinstance(self.mutations, str):
            self.mutations = await asyncio.to_thread(
                pl.read_csv, io.StringIO(self.mutations)
            )

        try:
            await asyncio.gather(
                self._save_alignment(), self._save_mutations(out, format)
            )
            return True

        except Exception as e:
            raise RuntimeError(f"Error saving mutations to {out}: {e}") from e

    async def _save_mutations(self, out, format):
        if format == "csv":
            await asyncio.to_thread(
                self.mutations.write_csv,
                out,
                include_header=True,
                separator=",",
            )
        elif format == "tsv":
            await asyncio.to_thread(
                self.mutations.write_csv,
                out,
                include_header=True,
                separator="\t",
            )
        elif format == "json":
            await asyncio.to_thread(self.mutations.write_json, out)
        else:
            raise ValueError(f"Unsupported format: {format}")

    @property
    def sequence_type(self) -> str:
        return "nucleotide"


class ProteinGroup(GroupAccessor):
    """
    Represents a Metagenomic Protein Group (protein-level operations).
    """

    @property
    def sequence_type(self) -> str:
        return "protein"
