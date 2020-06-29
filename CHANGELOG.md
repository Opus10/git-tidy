# Changelog
## 1.0.3 (2020-06-28)
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

