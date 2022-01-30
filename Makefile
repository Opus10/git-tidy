# Makefile for packaging and testing git-tidy
#
# This Makefile has the following targets:
#
# setup - Sets up the development environment
# clean-docs - Clean the documentation folder
# open-docs - Open any docs generated with "make docs"
# docs - Generated sphinx docs
# lint - Run code linting and static checks
# format - Format code using black
# test - Run tests using pytest
# full-test-suite - Run full test suite using tox
# shell - Run a shell in a virtualenv

OS = $(shell uname -s)
PACKAGE_NAME=git-tidy
MODULE_NAME=tidy
SHELL=bash

# Only mount the git config file when it exists. Otherwise Docker will create an empty directory
ifneq ($(wildcard ~/.gitconfig),) 
    GIT_CONFIG_DOCKER_MOUNT = -v ~/.gitconfig:/root/.gitconfig
endif 

# Docker run mounts the local code directory, SSH (for git), and global git config information
MAKE_CMD_WRAPPER?=docker run --rm -v $(shell pwd):/code -v ~/.ssh:/home/circleci/.ssh $(GIT_CONFIG_DOCKER_MOUNT) -it opus10/circleci-public-python-library


# Print usage of main targets when user types "make" or "make help"
.PHONY: help
help:
	@echo "Please choose one of the following targets: \n"\
	      "    setup: Setup development environment\n"\
	      "    test: Run tests\n"\
	      "    tox: Run tests against all versions of Python\n"\
	      "    lint: Run code linting and static checks\n"\
	      "    docs: Build Sphinx documentation\n"\
	      "    open-docs: Open built documentation\n"\
	      "\n"\
	      "View the Makefile for more documentation"
	@exit 2


# Install dependenies
.PHONY: dependencies
dependencies:
	$(MAKE_CMD_WRAPPER) poetry install


# Sets up development environment
.PHONY: setup
setup: dependencies
	$(MAKE_CMD_WRAPPER) poetry run git-tidy --template -o .gitcommit.tpl
	$(MAKE_CMD_WRAPPER) poetry run git config --local commit.template .gitcommit.tpl


# Get a shell into the development environment
.PHONY: shell
shell:
	$(MAKE_CMD_WRAPPER) /bin/bash


# Run pytest
.PHONY: test
test:
	$(MAKE_CMD_WRAPPER) poetry run pytest


# Run full test suite
.PHONY: full-test-suite
full-test-suite:
	$(MAKE_CMD_WRAPPER) poetry run tox


# Clean the documentation folder
.PHONY: clean-docs
clean-docs:
	-$(MAKE_CMD_WRAPPER) poetry run bash -c 'cd docs && make clean'


# Open the build docs (only works on Mac)
.PHONY: open-docs
open-docs:
ifeq (${OS}, Darwin)
	open docs/_build/html/index.html
else
	@echo "Open 'docs/_build/html/index.html' to view docs"
endif


# Build Sphinx autodocs
.PHONY: docs
docs: clean-docs  # Ensure docs are clean, otherwise weird render errors can result
	$(MAKE_CMD_WRAPPER) poetry run bash -c 'cd docs && make html'


# Run code linting and static analysis. Ensure docs can be built
.PHONY: lint
lint:
	$(MAKE_CMD_WRAPPER) poetry run black . --check
	$(MAKE_CMD_WRAPPER) poetry run flake8 -v ${MODULE_NAME}
	$(MAKE_CMD_WRAPPER) poetry run temple update --check
	$(MAKE_CMD_WRAPPER) poetry run bash -c 'cd docs && make html'


# Lint commit messages
.PHONY: check-changelog
check-changelog:
	$(MAKE_CMD_WRAPPER) poetry run git tidy-lint origin/master..


# Perform a tidy commit
.PHONY: tidy-commit
tidy-commit:
	$(MAKE_CMD_WRAPPER) poetry run git tidy-commit


# Perform a tidy squash
.PHONY: tidy-squash
tidy-squash:
	$(MAKE_CMD_WRAPPER) poetry run git tidy-squash origin/master


# Format code with black
.PHONY: format
format:
	$(MAKE_CMD_WRAPPER) poetry run black .


# Show the version the project. Used by CI and docs
.PHONY: _version
_version:
	-@poetry version | rev | cut -f 1 -d' ' | rev


# Show the name of the project
.PHONY: project-name
_project-name:
	-@poetry version | cut -d' ' -f1
