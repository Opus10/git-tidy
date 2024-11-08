# Changelog

## 1.3.0 (2024-11-01)

#### Changes

  - Added Python 3.13 support, dropped Python 3.8 support by [@wesleykendall](https://github.com/wesleykendall) in [#16](https://github.com/Opus10/git-tidy/pull/16).

## 1.2.2 (2024-08-24)

#### Changes

  - Updated docs styling and testing dependencies by [@wesleykendall](https://github.com/wesleykendall) in [#15](https://github.com/Opus10/git-tidy/pull/15).

## 1.2.1 (2024-04-23)

#### Trivial

  - Add Python 3.12 support and migrate docs to Mkdocs. [Wes Kendall, 48d0e54]

## 1.2.0 (2023-03-26)

#### Bug

  - Fix errors parsing hyphenated trailers [Wesley Kendall, 1938c49]

    Trailers such as Co-authored-by were not correctly parsed by git-tidy.
    Users can now correctly supply hyphenated trailers manually, and they
    can also specify attributes with underscores in the commit message
    schema.

## 1.1.5 (2022-08-24)

#### Trivial

  - Update with the latest Python library template [Opus 10 Devops, f7ae7e2]

## 1.1.4 (2022-07-31)

#### Trivial

  - Updates with latest Python template, fixing doc builds [Opus 10 Devops, d24c01b]

## 1.1.3 (2022-03-19)

#### Trivial

  - Updated with the latest template, which upgrades local Docker development [Opus 10 Devops, 9a5a1b6]

## 1.1.2 (2022-01-31)

#### Trivial

  - Minor docker development fixes [Opus 10 Devops, 25633a5]

## 1.1.1 (2022-01-31)

#### Trivial

  - Updated with the latest version of the template, which drops Python 3.6 support and adds Python 3.10 support [Opus 10 Devops, aa8e925]

## 1.1.0 (2021-12-15)

#### Bug

  - Fix git versions installed on Mac [Wes Kendall, 2c7e268]

    The return of ``git --version`` on Macs produce a different version string that
    was previously not supported in git-tidy. This is now fixed.

## 1.0.5 (2021-12-15)

#### Trivial

  - Update to the latest Python template [Wes Kendall, d961605]

## 1.0.4 (2021-05-29)

#### Trivial

  - Updated with latest Python template [Wes Kendall, 38da743]

## 1.0.3 (2020-06-29)

#### Trivial

  - Fixed link to image in README. [Wes Kendall, 825c511]

## 1.0.2 (2020-06-25)

#### Trivial

  - Add additional README docs and homebrew install instructions. [Wes Kendall, bb7859e]

## 1.0.1 (2020-06-24)

#### Trivial

  - Added more package metadata and use git-tidy to generate ChangeLog. [Wes Kendall, 0c7c000]

## 1.0.0 (2020-06-24)

#### Api-Break

  - The initial release of git-tidy [Wes Kendall, 2968d20]

    ``git-tidy`` provides git extensions for making tidy commits,
    enforcing commit structure, and rendering structured commit logs.
    V1 comes with the following commands:

    - ``git tidy`` - Prints version information.
    - ``git tidy-commit`` - Performs a tidy commmit.
    - ``git tidy-lint`` - Lints commit messages.
    - ``git tidy-log`` - Renders tidy commit messages.
