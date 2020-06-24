"""
The tidy CLI contains commands for doing tidy commits, linting the
commits, and rendering the log.

Commands
~~~~~~~~

* ``git-tidy`` - Prints version information
* ``git-tidy-commit`` - Performs a tidy commit
* ``git-tidy-log`` - Renders templated commit messages
* ``git-tidy-lint`` - Validates structure of commit messages
* ``git-tidy-squash`` - Squashes commit messages into a single tidy commit
"""
import sys

import click
import pkg_resources

from tidy import core


@click.command()
@click.option('--template', help='Show tidy commit template.', is_flag=True)
@click.option(
    '-o', '--output', help='Output file name of the commit template.'
)
def tidy(template, output):
    """
    Print version information about ``git-tidy`` or show the tidy commit
    template.
    """
    if not template:
        click.echo(
            f'git-tidy {pkg_resources.get_distribution("git-tidy").version}'
        )
    else:
        core.commit_template(output=output or sys.stdout)


@click.command()
@click.option('--no-verify', help='Disable running hooks.', is_flag=True)
@click.option('--allow-empty', help='Allow an empty commit.', is_flag=True)
@click.pass_context
def commit(ctx, no_verify, allow_empty):
    """
    Perform a tidy commit.
    """
    result = core.commit(no_verify=no_verify, allow_empty=allow_empty)
    ctx.exit(result.returncode)


@click.command()
@click.argument('range', nargs=-1)
@click.option(
    '--any',
    is_flag=True,
    help='Make linting pass if at least one commit is valid',
)
@click.pass_context
def lint(ctx, range, any):
    """
    Run tidy commit linting against a range of commits.

    If ``:github/pr`` is provided as the range, the base branch of the pull
    request will be used as the revision range (e.g. ``origin/develop..``).
    """
    range = ' '.join(range)
    is_valid, commits = core.lint(range, any=any)

    if not is_valid:
        failures = commits.filter('is_valid', False)
        err_msg = (
            f'{len(failures)} out of {len(commits)} commits'
            f' have failed linting:'
        )
        click.echo(click.style(err_msg, fg='red'), err=True)

        for failure in failures:
            click.echo(f'{failure.sha}: {failure.validation_errors}', err=True)
        ctx.exit(1)


@click.command()
@click.argument('range', nargs=-1)
@click.option('--style', default='default')
@click.option(
    '--tag-match',
    help=(
        'A glob(7) pattern for matching tags when associating a tag with a'
        ' commit in the log. Passed to ``git describe --contains --matches``'
        ' when associating a tag with a commit.'
    ),
)
@click.option('--before', help='Filter commits before a date.')
@click.option('--after', help='Filter commits after a date.')
@click.option('--reverse', help='Reverse ordering of results.', is_flag=True)
@click.option('-o', '--output', help='Output file name of the log.')
def log(range, style, tag_match, before, after, reverse, output):
    """
    Run tidy log output against a range of commits.

    If ``:github/pr`` is provided as the range, the base branch of the pull
    request will be used as the revision range (e.g. ``origin/develop..``).
    If ``:github/pr`` is used as the output target, the log will be written
    as a comment on the current Github pull request.
    """
    range = ' '.join(range)
    core.log(
        range,
        style=style,
        tag_match=tag_match,
        before=before,
        after=after,
        reverse=reverse,
        output=output or sys.stdout,
    )


@click.command()
@click.argument('ref')
@click.option('--no-verify', help='Disable running hooks.', is_flag=True)
@click.option('--allow-empty', help='Allow an empty commit.', is_flag=True)
@click.pass_context
def squash(ctx, ref, no_verify, allow_empty):
    """
    Squash commits from ref commit into a single commit.

    If ``:github/pr`` is provided as the ref, the base branch of the pull
    request will be used (e.g. ``origin/develop``).
    """
    commit_result = core.squash(
        ref, no_verify=no_verify, allow_empty=allow_empty
    )
    ctx.exit(commit_result.returncode)
