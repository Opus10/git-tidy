# Changelog
## 1.1.2 (2022-01-30)
### Trivial
  - Minor docker development fixes [Opus 10 Devops, 25633a5]

## 1.1.1 (2022-01-31)
### Trivial
  - Updated with the latest version of the template, which drops Python 3.6 support and adds Python 3.10 support [Opus 10 Devops, aa8e925]

## 1.1.0 (2021-12-15)
### Bug
  - Fix git versions installed on Mac [Wes Kendall, 2c7e268]

    The return of ``git --version`` on Macs produce a different version string that
    was previously not supported in git-tidy. This is now fixed.

## 1.0.5 (2021-12-15)
### Trivial
  - Update to the latest Python template [Wes Kendall, d961605]

## 1.0.4 (2021-05-29)
### Trivial
  - Updated with latest Python template [Wes Kendall, 38da743]

## 1.0.3 (2020-06-29)
### Trivial
  - Fixed link to image in README. [Wes Kendall, 825c511]

## 1.0.2 (2020-06-25)
### Trivial
  - Add additional README docs and homebrew install instructions. [Wes Kendall, bb7859e]

## 1.0.1 (2020-06-24)
### Trivial
  - Added more package metadata and use git-tidy to generate ChangeLog. [Wes Kendall, 0c7c000]

## 1.0.0 (2020-06-24)
### Api-Break
  - The initial release of git-tidy [Wes Kendall, 2968d20]

    ``git-tidy`` provides git extensions for making tidy commits,
    enforcing commit structure, and rendering structured commit logs.
    V1 comes with the following commands:

    - ``git tidy`` - Prints version information.
    - ``git tidy-commit`` - Performs a tidy commmit.
    - ``git tidy-lint`` - Lints commit messages.
    - ``git tidy-log`` - Renders tidy commit messages.

