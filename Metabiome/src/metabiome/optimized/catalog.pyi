"""
Type stubs for optimized.catalog Cython module.

This file provides type hints for the high-performance sequence analysis functions
compiled with Cython. It enables proper IDE support and static type checking.
"""

from typing import Any, Tuple

import numpy as np
from numpy.typing import NDArray

def codon_to_aa(
    name: bytes, sequence: bytes, table: int
) -> Tuple[bytes, bytes, NDArray[np.uint8]]:
    """
    Translate nucleotide sequence to amino acids.

    Parameters
    ----------
    name : bytes
        Sequence identifier
    sequence : bytes
        Nucleotide sequence (must be multiple of 3)
    table : int
        Genetic code table number

    Returns
    -------
    Tuple[bytes, bytes, NDArray[np.uint8]]
        (name, amino_acid_sequence, codon_array)

    Raises
    ------
    ValueError
        If sequence length is not multiple of 3 or contains invalid codons
    """
    ...

def classify_mutations(
    identifier: bytes,
    sequence: bytes,
    consensus: bytes,
    table: int,
    buffer: Any,
) -> None:
    """
    Classify non-silent mutations compared to consensus sequence.

    Parameters
    ----------
    identifier : bytes
        Sequence identifier
    sequence : bytes
        Nucleotide sequence to analyze
    consensus : bytes
        Consensus nucleotide sequence for comparison
    table : int
        Genetic code table number
    buffer : Any
        File-like object to write CSV mutation data

    Returns
    -------
    None
        Writes mutation classifications to buffer
    """
    ...

def protein_to_nucleotide(
    seq_id: Any, gapped_prot_seq: bytes, mapping: NDArray[np.uint8]
) -> Any:
    """
    Map gapped protein sequence back to nucleotide sequence.

    Parameters
    ----------
    seq_id : Any
        Sequence identifier
    gapped_prot_seq : bytes
        Protein sequence with gaps
    mapping : NDArray[np.uint8]
        Codon mapping array (n_amino_acids, 3)

    Returns
    -------
    Any
        GappedSequence object with nucleotide sequence

    Raises
    ------
    MemoryError
        If memory allocation fails
    """
    ...

def get_most_common_base(
    input_vector: NDArray[np.uint8], threshold: float, include_gaps: bool
) -> int:
    """
    Find the most common base in a column of sequence alignment.

    Parameters
    ----------
    input_vector : NDArray[np.uint8]
        Column of bases from alignment
    threshold : float
        Minimum frequency threshold (0.0-1.0)
    include_gaps : bool
        Whether to include gap characters in counting

    Returns
    -------
    int
        ASCII code of most common base, or gap character if none meets threshold
    """
    ...

def calculate_average_pid(
    matrix: NDArray[np.uint8], reference: NDArray[np.uint8]
) -> float:
    """
    Calculate average percentage identity against reference sequence.

    Parameters
    ----------
    matrix : NDArray[np.uint8]
        2D array of sequences (rows=sequences, cols=positions)
    reference : NDArray[np.uint8]
        1D reference sequence array

    Returns
    -------
    float
        Average percentage identity (0.0-1.0)
    """
    ...


def calculate_positional_pid(
    matrix: NDArray[np.uint8], reference: NDArray[np.uint8]
) -> NDArray[np.float32]:
    """
    Calculate percentage identity for each position against a reference.

    Parameters
    ----------
    matrix : NDArray[np.uint8]
        2D array of sequences (rows=sequences, cols=positions).
    reference : NDArray[np.uint8]
        1D reference sequence array.

    Returns
    -------
    NDArray[np.float32]
        An array of percentage identity values (0.0-100.0), one for each position.
    """
    ...
