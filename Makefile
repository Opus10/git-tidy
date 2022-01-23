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
DOCKER_RUN=docker run --rm -v $(shell pwd):/code -v ~/.ssh:/root/.ssh $(GIT_CONFIG_DOCKER_MOUNT) -it opus10/git-tidy


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


# Sets up development environment
.PHONY: setup
setup:
	docker build . --rm -t opus10/git-tidy


# Get a shell into the development environment
.PHONY: shell
shell:
	$(DOCKER_RUN) poetry shell


# Run pytest
.PHONY: test
test:
	$(DOCKER_RUN) poetry run pytest


# Run full test suite in CI
.PHONY: _full-test-suite
_full-test-suite:
	poetry run tox

# Run full test suite
.PHONY: full-test-suite
full-test-suite:
	$(DOCKER_RUN) make _full-test-suite


# Clean the documentation folder
.PHONY: clean-docs
clean-docs:
	-$(DOCKER_RUN) bash -c 'cd docs && make clean'


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
	$(DOCKER_RUN) bash -c 'cd docs && make html'	


# Core linting command used in CI
.PHONY: _lint
_lint:
	poetry run black . --check
	poetry run flake8 -v ${MODULE_NAME}
	poetry run temple update --check
	cd docs && make html


# Run code linting and static analysis. Ensure docs can be built
.PHONY: lint
lint:
	$(DOCKER_RUN) make _lint


# Lint commit messages on CI
.PHONY: _check-changelog
_check-changelog:
	poetry run git tidy-lint origin/master


# Lint commit messages
.PHONY: check-changelog
check-changelog:
	$(DOCKER_RUN) make _check-changelog


# Perform a tidy commit
.PHONY: tidy-commit
tidy-commit:
	$(DOCKER_RUN) poetry run git tidy-commit


# Perform a tidy squash
.PHONY: tidy-squash
tidy-squash:
	$(DOCKER_RUN) poetry run git tidy-squash origin/master


# Format code with black
.PHONY: format
format:
	$(DOCKER_RUN) poetry run black .


# Show the version the project. Used by CI and docs
.PHONY: _version
_version:
	-@poetry version | rev | cut -f 1 -d' ' | rev


# Show the name of the project
.PHONY: project-name
_project-name:
	-@poetry version | cut -d' ' -f1
