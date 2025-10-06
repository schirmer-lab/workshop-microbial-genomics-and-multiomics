"""
Centralized error/exception classes for metabiome.
"""


class ContainerIndexError(IndexError):
    """Specific exception for container indexing errors."""

    pass


class ContainerKeyError(KeyError):
    """Specific exception for container key errors."""

    pass


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass
