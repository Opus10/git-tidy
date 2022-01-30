Contributing Guide
==================

This project was created using temple.
For more information about temple, go to the
`Temple docs <https://github.com/CloverHealth/temple>`_.

Setup
~~~~~

Set up your development environment with::

    git clone git@github.com:Opus10/git-tidy.git
    cd git-tidy
    make setup

``make setup`` will set up a development environment managed by Docker.
Install docker `here <https://www.docker.com/get-started>`_.


Testing and Validation
~~~~~~~~~~~~~~~~~~~~~~

Run the tests on one Python version with::

    make test

Run the full test suite against all supported Python versions with::

    make full-test-suite

Validate the code with::

    make lint

If your code fails the ``black`` check, automatically format your code with::

    make format

Committing
~~~~~~~~~~

`git-tidy <https://github.com/Opus10/git-tidy>`_ is used to produce structured
commits with git trailers. Git commits are validated in continuous integration
because we use the information from them to generate release notes and
bump library versions.

To do a structured commit with ``git-tidy``, do::

    make tidy-commit

All commits in a pull request must be tidy commits that encapsulate a
change. Ideally entire features or bug fixes are encapsulated in a
single commit. Squash all of your commits into a tidy commit with::

    make tidy-squash

To check if your commits pass linting, do::

    make tidy-lint

Note, the above command lints every commit since branching from master.
You can also run ``make shell`` and run ``git tidy`` commands inside
the docker environment.

Documentation
~~~~~~~~~~~~~

`Sphinx <http://www.sphinx-doc.org/>`_ documentation can be built with::

    make docs

The static HTML files are stored in the ``docs/_build/html`` directory.
A shortcut for opening them (on OSX) is::

    make open-docs

Releases and Versioning
~~~~~~~~~~~~~~~~~~~~~~~

Anything that is merged into the master branch will be automatically deployed
to PyPI. Documentation will be published to a ReadTheDocs at
``https://git-tidy.readthedocs.io/``.

The following files will be generated and should *not* be edited by a user:

* ``CHANGELOG.md`` - Contains an automatically-generated change log for
  each release.

This project uses `Semantic Versioning <http://semver.org>`_ by analyzing
``Type:`` trailers on git commit messages (trailers are added when using
``git tidy-commit``). In order to bump the minor
version, use "feature" or "bug" as the type.
In order to bump the major version, use "api-break". The patch version
will be updated automatically if none of these tags are present.
