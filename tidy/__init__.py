"""
The core ``git-tidy`` functions and classes that are utilized by
the :ref:`cli`.
"""

from tidy.core import Commit, CommitRange, Commits, Tag, commit, lint, log, squash
from tidy.version import __version__

__all__ = [
    "commit",
    "lint",
    "log",
    "squash",
    "Commit",
    "Commits",
    "CommitRange",
    "Tag",
    "__version__",
]
