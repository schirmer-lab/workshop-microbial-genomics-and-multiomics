"""
Centralized warning classes for metabiome (extend as needed).
"""


class MetabiomeWarning(Warning):
    """Base warning for metabiome package."""

    pass


class ImplicitModificationWarning(UserWarning):
    """Warning for implicit modification of data structures.

    This warning is raised when a data structure is modified in place
    without an explicit copy, which may lead to unexpected behavior.
    """

    pass
