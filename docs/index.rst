git-tidy
========

``git-tidy`` is a set of git extensions for keeping your git logs tidy
and rendering tidy release notes. When installed, the following git
subcommands are available:

1. ``git tidy`` - Prints version information of ``git-tidy``
2. ``git tidy-commit`` - Performs a tidy commit.
3. ``git tidy-lint`` - Lints commit messages.
4. ``git tidy-log`` - Renders a tidy log.
5. ``git tidy-squash`` - Squashes commits into a single tidy commit.

``git-tidy`` commit messages are structured based on a user-defined
``formaldict`` schema stored in the repository. Users specify all
attributes that are collected during tidy commits in the schema. All of
this structured information can be linted (``git tidy-lint``) in a continuous
integration (CI) process, and the structured information can be rendered
(``git tidy-log``) with a user-supplied Jinja template inside their repository.

See the :ref:`tutorial` for a walk-through of how to use ``git-tidy`` for your
use case.
