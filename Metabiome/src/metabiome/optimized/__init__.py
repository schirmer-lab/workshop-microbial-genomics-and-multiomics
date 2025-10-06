"""
High-performance optimized functions using Cython.

This module contains performance-critical sequence analysis functions
compiled with Cython for maximum speed.
"""

# Import the compiled Cython functions
try:
    from .catalog import (
        calculate_average_pid,
        calculate_positional_pid,
        classify_mutations,
        codon_to_aa,
        get_most_common_base,
        protein_to_nucleotide,
    )
except ImportError:

    def classify_mutations(*args, **kwargs):
        raise ImportError(
            "Cython extension not available. Run 'uv run python setup.py build_ext --inplace'"
        )

    def codon_to_aa(*args, **kwargs):
        raise ImportError(
            "Cython extension not available. Run 'uv run python setup.py build_ext --inplace'"
        )

    def get_most_common_base(*args, **kwargs):
        raise ImportError(
            "Cython extension not available. Run 'uv run python setup.py build_ext --inplace'"
        )

    def protein_to_nucleotide(*args, **kwargs):
        raise ImportError(
            "Cython extension not available. Run 'uv run python setup.py build_ext --inplace'"
        )

    def calculate_average_pid(*args, **kwargs):
        raise ImportError(
            "Cython extension not available. Run 'uv run python setup.py build_ext --inplace'"
        )

    def calculate_positional_pid(*args, **kwargs):
        raise ImportError(
            "Cython extension not available. Run 'uv run python setup.py build_ext --inplace'"
        )


__all__ = [
    "classify_mutations",
    "codon_to_aa",
    "get_most_common_base",
    "protein_to_nucleotide",
    "calculate_average_pid",
    "calculate_positional_pid",
]
