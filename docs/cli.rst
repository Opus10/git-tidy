.. _cli:

Tidy CLI
========

The main ``git-tidy`` commands are listed below. Note that
``--help`` can be given as an argument to any of these commands to print
out help on the command line.

.. click:: tidy.cli:tidy
  :prog: git-tidy
  :show-nested:

.. click:: tidy.cli:commit
  :prog: git-tidy-commit
  :show-nested:

.. click:: tidy.cli:lint
  :prog: git-tidy-lint
  :show-nested:

.. click:: tidy.cli:log
  :prog: git-tidy-log
  :show-nested:

.. click:: tidy.cli:squash
  :prog: git-tidy-squash
  :show-nested:
