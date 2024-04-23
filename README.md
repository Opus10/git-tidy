# git-tidy

`git-tidy` is a set of git extensions for:

1. Keeping your git logs tidy with ease. `git tidy-commit` guides users through a structured commit with a configurable schema. `git tidy-squash` squashes messy commits into one tidy commit.
2. Linting a commit log. `git tidy-lint` verifies that commits match the schema. If a user uses `git tidy-commit`, commits will *always* validate.
3. Rendering a commit log. `git tidy-log` can render commits from any range and can render structured commits from a configurable [Jinja](https://jinja.palletsprojects.com/en/2.11.x/) template. Want to automatically generate release notes? `git tidy-log` can be configured to group and render commits based on the schema.

![Example](https://raw.githubusercontent.com/jyveapp/git-tidy/main/docs/static/tidy-commit.gif)

## Documentation

[View the git-tidy docs here](https://git-tidy.readthedocs.io/) for a complete tutorial on using `git-tidy`.

## Installation

One can install `git-tidy` system-wide with [pipx](https://github.com/pipxproject/pipx):

    pipx install git-tidy

or pip:

    pip3 install git-tidy

**Note** `git-tidy` depends on git at a version of 2.22 or higher. OSX users can upgrade to the latest `git` version with [homebrew](brew.sh) using `brew install git`.

## Compatibility

`git-tidy` is compatible with Python 3.8 - 3.12.

## Contributing Guide

For information on setting up git-tidy for development and contributing changes, view `CONTRIBUTING.rst <CONTRIBUTING.rst>`_.

## Creators

- @wesleykendall (Wes Kendall)
- @tomage (Tómas Árni Jónasson)
