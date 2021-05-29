Installation
============

``git-tidy`` can be installed a number of ways. The preferred way
on OSX is with homebrew::

    brew tap opus10/homebrew-tap
    brew install git-tidy

If not on OSX, one can install ``git-tidy`` system-wide with
`pipx <https://github.com/pipxproject/pipx>`__::

    pipx install git-tidy

``git-tidy`` can also be installed with pip. Be sure to install it system-wide
so that ``git-tidy``'s execution is not tied to a virtual environment::

    pip3 install git-tidy

Verify your installation by typing ``git tidy``.

.. note::

  ``git-tidy`` depends on git at a version of 2.22 or higher. OSX
  users can upgrade to the latest ``git`` version with
  `homebrew <brew.sh>`__ using ``brew install git``.
