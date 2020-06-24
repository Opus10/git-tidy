"""Integration tests for git-tidy"""
from contextlib import ExitStack as does_not_raise
import io
import os

import formaldict
import jinja2.exceptions
import pytest

from tidy import core
from tidy import exceptions
from tidy import utils


@pytest.fixture()
def tidy_config(tmp_path, mocker):
    """Creates an example tidy configuration for integration tests"""
    tidy_root = tmp_path / '.git-tidy'
    tidy_root.mkdir()

    tidy_commit_config = tidy_root / 'commit.yaml'
    tidy_commit_config.write_text(
        '- label: type\n'
        '  name: Type\n'
        '  help: The type of change.\n'
        '  type: string\n'
        '  choices:\n'
        '      - api-break\n'
        '      - bug\n'
        '      - feature\n'
        '      - trivial\n'
        '\n'
        '- label: summary\n'
        '  name: Summary\n'
        '  help: A high-level summary of the changes.\n'
        '  type: string\n'
        '\n'
        '- label: description\n'
        '  name: Description\n'
        '  help: An in-depth description of the changes.\n'
        '  type: string\n'
        '  condition: ["!=", "type", "trivial"]\n'
        '  multiline: True\n'
        '  required: False\n'
        '\n'
        '- label: jira\n'
        '  name: Jira\n'
        '  help: Jira Ticket ID.\n'
        '  type: string\n'
        '  required: false\n'
        '  condition: ["!=", "type", "trivial"]\n'
        '  matches: WEB-[\\d]+\n'
        '\n'
        '- label: component\n'
        '  type: string\n'
        '  required: false\n'
        '  condition: ["!=", "type", "trivial"]\n'
    )

    tidy_commit_template = tidy_root / 'log.tpl'
    tidy_commit_template.write_text(
        '{% for tag, commits_by_tag in commits.group("tag").items() %}\n'
        '# {{ tag|default("Unreleased", True) }} '
        '{% if tag.date %}({{ tag.date.date() }}){% endif %}\n'
        '\n'
        '{% for type, commits_by_type in '
        'commits_by_tag.group("type", '
        'ascending_keys=True, none_key_last=True).items() %}\n'
        '## {{ type|default("Other", True)|title }}\n'
        '{% for commit in commits_by_type %}\n'
        '{% if not commit.is_parsed %}\n'
        '- {{ commit.sha }}: Commit could not be parsed.\n'
        '{% else %}\n'
        '- {{ commit.summary }} [{{ commit.author_name }}, {{ commit.sha }}]\n'
        '{% if commit.description %}\n'
        '\n'
        '  {{ commit.description }}\n'
        '{% endif %}\n'
        '{% endif %}\n'
        '{% endfor %}\n'
        '{% endfor %}\n'
        '\n'
        '{% endfor %}\n'
    )

    mocker.patch(
        'tidy.utils.get_tidy_file_root',
        return_value=str(tidy_root),
        autospec=True,
    )

    yield tmp_path


@pytest.fixture()
def git_tidy_repo(tidy_config):
    """Create a git repo with structured commits for integration tests"""
    cwd = os.getcwd()
    os.chdir(tidy_config)

    utils.shell('git init .')
    utils.shell('git config user.email "you@example.com"')
    utils.shell('git config user.name "Your Name"')
    utils.shell(
        'git commit --allow-empty -m $"Summary1 [skip ci]\n\n'
        'Description1\n\nType: api-break\nJira: WEB-1111"'
    )
    utils.shell(
        'git commit --allow-empty -m $"Summary2\n\nDescription2\n\n'
        'Type: bug\nJira: WEB-1112"'
    )
    utils.shell('git tag v1.1')
    utils.shell('git commit --allow-empty -m $"Summary3\n\nType: trivial"')
    utils.shell('git tag dev1.2')
    utils.shell('git tag v1.2')
    utils.shell(
        'git commit --allow-empty -m $"Summary4\n\nDescription4\n\n'
        'Type: feature\nJira: WEB-1113"'
    )
    utils.shell(
        'git commit --allow-empty -m $"Invalid5\n\n'
        'Type: feature\nJira: INVALID"'
    )
    # Create a commit that uses the same delimiter structure as git-tidy
    # to create a scenario of an unparseable commit.
    utils.shell('git commit --allow-empty -m $"Invalid6\n\nUnparseable: *{*"')

    yield tidy_config

    os.chdir(cwd)


@pytest.mark.usefixtures('git_tidy_repo')
def test_tidy_log():
    """
    Integration test for tidy-log
    """
    full_log = utils.shell_stdout('git tidy-log')
    assert full_log.startswith('# Unreleased')
    assert 'Commit could not be parsed.' in full_log
    assert '# v1.2' not in full_log  # dev1.2 takes precedence in this case
    assert '# dev1.2' in full_log
    assert '# v1.1' in full_log


@pytest.mark.usefixtures('git_tidy_repo')
def test_commit_properties_and_range_filtering(mocker):
    """
    Integration test for core.CommitRange filtering, grouping, and excluding
    and core Commit properties
    """
    cr = core.CommitRange()

    # Check various commit properties
    invalid_commit = list(
        cr.filter('is_valid', False).filter('is_parsed', True)
    )[0]
    assert (
        str(invalid_commit.validation_errors)
        == 'jira: Value "INVALID" does not match pattern "WEB-[\\d]+".'
    )
    assert invalid_commit.type == 'feature'
    assert not invalid_commit.is_valid
    with pytest.raises(AttributeError):
        invalid_commit.invalid_attribute
    assert invalid_commit.msg.startswith('sha: ')
    assert invalid_commit.jira is None
    assert invalid_commit.tag is None

    api_break_commit = list(cr.filter('type', 'api-break'))[0]
    assert str(api_break_commit.tag) == 'v1.1'

    # Check various filterings on the range
    assert len(cr.filter('is_valid', True)) == 4
    assert len(cr.filter('is_valid', False)) == 2
    assert len(cr.exclude('is_valid', False)) == 4
    assert len(cr.filter('is_parsed', False)) == 1
    assert len(cr.filter('type', 'feature').filter('is_valid', True)) == 1
    assert len(cr.filter('summary', r'.*\[skip ci\].*', match=True)) == 1
    assert len(cr.exclude('summary', r'.*\[skip ci\].*', match=True)) == 5

    # Check groupings
    tag_groups = cr.group('tag')
    assert len(tag_groups) == 3
    assert len(tag_groups[None]) == 3
    assert len(tag_groups['v1.1']) == 2
    assert len(tag_groups['dev1.2']) == 1
    assert len(tag_groups[None].group('type')) == 2
    assert list(tag_groups['v1.1'].group('type', ascending_keys=True)) == [
        'api-break',
        'bug',
    ]

    type_groups = cr.group('type')
    assert len(type_groups) == 5
    assert len(type_groups[None]) == 1
    assert len(type_groups['api-break']) == 1
    assert len(type_groups['bug']) == 1
    assert len(type_groups['feature']) == 2
    assert len(type_groups['trivial']) == 1

    # Check group sorting
    assert list(cr.group('tag', ascending_keys=True)) == [
        'dev1.2',
        'v1.1',
        None,
    ]
    assert list(cr.group('tag', descending_keys=True)) == [
        'v1.1',
        'dev1.2',
        None,
    ]
    assert list(cr.group('tag', ascending_keys=True, none_key_first=True)) == [
        None,
        'dev1.2',
        'v1.1',
    ]
    assert list(
        cr.group('tag', descending_keys=True, none_key_first=True)
    ) == [None, 'v1.1', 'dev1.2']

    # Try matching on the v* tags (no dev tags)
    cr = core.CommitRange(tag_match='v*')
    assert set(cr.group('tag')) == {None, 'v1.1', 'v1.2'}

    # Try before/after filtering
    assert not list(core.CommitRange(before='2019-01-01'))
    assert len(core.CommitRange(after='2019-01-01')) == 6
    assert not list(core.CommitRange(after='2019-01-01', before='2019-01-01'))

    # Try reversing commits
    assert (
        list(core.CommitRange(tag_match='v*', reverse=True))[0].type
        == 'api-break'
    )

    # Get a commit range over a github PR
    mocker.patch(
        'tidy.core._get_pull_request_range', autospec=True, return_value=''
    )

    cr = core.CommitRange(':github/pr')
    assert len(cr) == 6


@pytest.mark.parametrize(
    'input_data',
    [
        {
            'type': 'bug',
            'summary': 'summary!',
            'description': 'description!',
            'jira': 'WEB-9999',
        },
        # Tests a scenario where a key is empty. This
        # previously caused commit parsing issues.
        {
            'type': 'feature',
            'summary': 'summary',
            'description': 'description',
            'jira': '',
        },
        # Tests a scenario where twos keys are empty.
        {
            'type': 'feature',
            'summary': 'summary',
            'description': 'description',
            'jira': '',
            'component': '',
        },
        # Tests where a key in the middle of the final message is empty
        {
            'type': 'feature',
            'summary': 'summary',
            'description': 'description',
            'jira': '',
            'component': 'django',
        },
        # Tests committing key with double quotes
        {
            'type': 'feature',
            'summary': 'summary',
            'description': '"description"',
            'jira': '',
            'component': '"""',
        },
        # Tests no trailers
        {'summary': 'summary'},
    ],
)
@pytest.mark.usefixtures('git_tidy_repo')
def test_commit(mocker, input_data):
    """Tests core.commit and verifies the resulting commit object."""
    mocker.patch.object(
        formaldict.Schema, 'prompt', autospec=True, return_value=input_data
    )

    with open('file_to_commit', 'w+') as f:
        f.write('Hello World')

    utils.shell('git add .')
    assert core.commit().returncode == 0

    commit = core.CommitRange('HEAD~1..')[0]
    assert commit.is_parsed
    for key, value in input_data.items():
        assert getattr(commit, key) == value


@pytest.mark.usefixtures('git_tidy_repo')
def test_empty_commit(mocker):
    """Tests core.commit() with empty commit and no commit message"""
    mocker.patch.object(
        formaldict.Schema, 'prompt', autospec=True, return_value={}
    )

    # Git does not allow empty commit messages
    assert core.commit(allow_empty=True).returncode == 1


@pytest.mark.usefixtures('git_tidy_repo')
def test_empty_commit_not_allowed():
    """Tests core.commit() with an empty commit when its not allowed"""
    assert core.commit().returncode == 1


@pytest.mark.parametrize('pre_commit_return', [1, 0])
@pytest.mark.usefixtures('git_tidy_repo')
def test_commit_w_pre_commit_hook(pre_commit_return, mocker):
    """Tests core.commit() with a pre commit hook"""
    with open('.git/hooks/pre-commit', 'w+') as f:
        f.write(f'#!/bin/bash\nexit {pre_commit_return}')
    os.chmod('.git/hooks/pre-commit', 0o777)

    mocker.patch.object(
        formaldict.Schema,
        'prompt',
        autospec=True,
        return_value={
            'type': 'bug!',
            'summary': 'summary!',
            'description': 'description!',
            'jira': 'WEB-9999',
        },
    )

    assert core.commit(allow_empty=True).returncode == pre_commit_return


@pytest.mark.parametrize('any', [True, False])
@pytest.mark.usefixtures('git_tidy_repo')
def test_lint(any):
    """Tests core.lint()"""
    passed, commits = core.lint(any=any)
    assert passed == any
    assert len(commits) == 6


@pytest.mark.parametrize(
    'output', [None, 'output_file', io.StringIO(), ':github/pr']
)
@pytest.mark.usefixtures('git_tidy_repo')
def test_log(output, mocker):
    """Tests core.log() with various output targets"""
    patched_github = mocker.patch('tidy.github.comment', autospec=True)
    rendered = core.log(output=output)

    if isinstance(output, str) and output != ':github/pr':
        with open(output) as f:
            rendered = f.read()
    elif output == ':github/pr':
        assert patched_github.called
    elif output is not None:
        rendered = output.getvalue()

    assert rendered.startswith('# Unreleased')
    assert 'Commit could not be parsed' in rendered
    assert '# dev1.2 (' in rendered
    assert '## Api-Break' in rendered


@pytest.mark.parametrize(
    'style, expected_exception',
    [
        ('default', does_not_raise()),
        (
            'custom',
            pytest.raises(
                jinja2.exceptions.TemplateNotFound, match='log_custom.tpl'
            ),
        ),
    ],
)
@pytest.mark.usefixtures('git_tidy_repo')
def test_log_no_template(style, expected_exception):
    """
    Tests core.log() when no template is present. The default tidy template
    should be used when the default style is provided
    """
    os.remove('.git-tidy/log.tpl')
    with expected_exception:
        rendered = core.log(style=style)

        assert '# v1.2' not in rendered  # dev1.2 takes precedence in this case
        assert '# dev1.2' in rendered
        assert '# v1.1' in rendered
        assert 'Unreleased' in rendered
        assert 'Description1' in rendered
        assert 'Summary1' in rendered


def test_tidy_template():
    """Tests core.commit_template() by rendering git-tidy's commit template"""
    rendered = core.commit_template()

    assert rendered == (
        '# Remember - commit messages are used to generate release notes!\n'
        '# Use the following template when writing a commit message or\n'
        '# use "git tidy-commit" to commit a properly-formatted message.\n'
        '#\n'
        '# ---- Commit Message Format ----\n'
        '#\n'
        '# A high-level summary of the changes.\n'
        '#\n'
        '# An in-depth description of the changes.\n'
        '#\n'
        '# Type: The type of change.\n'
    )


@pytest.mark.usefixtures('git_tidy_repo')
def test_squash(mocker):
    """Tests core.squash"""
    mocker.patch.object(
        formaldict.Schema,
        'prompt',
        autospec=True,
        side_effect=[
            {
                # The first commit
                'type': 'bug',
                'summary': 'summary',
                'description': 'description',
                'jira': 'WEB-9999',
            },
            {
                # The second commit
                'type': 'trivial',
                'summary': 'Fixing up something',
            },
            {
                # The third commit
                'type': 'trivial',
                'summary': 'Fixing up something else',
            },
            {
                # The commit when squashing all commits
                'type': 'bug',
                'summary': 'final summary',
                'description': 'final description',
                'jira': 'WEB-9999',
            },
        ],
    )

    for f_name in ['file_to_commit1', 'file_to_commit2', 'file_to_commit3']:
        with open(f_name, 'w+') as f:
            f.write('Hello World')

        utils.shell('git add .')
        assert core.commit().returncode == 0

    assert core.squash('HEAD~2').returncode == 0

    commit = utils.shell_stdout('git show --summary')
    assert (
        '    final summary\n'
        '    \n'
        '    final description\n'
        '    \n'
        '    Type: bug\n'
        '    Jira: WEB-9999'
    ) in commit


@pytest.mark.usefixtures('git_tidy_repo')
def test_squash_diverging_branches(mocker):
    """Tests core.squash against a base branch that has diverged"""
    mocker.patch.object(
        formaldict.Schema,
        'prompt',
        autospec=True,
        side_effect=[
            {
                # The first commit on the base branch
                'type': 'bug',
                'summary': 'summary',
                'description': 'first master commit',
                'jira': 'WEB-9999',
            },
            {
                # The second commit on base after making squash branch
                'type': 'trivial',
                'summary': 'wont be seen in history',
            },
            {
                # The first commit on the branch to squash
                'type': 'trivial',
                'summary': 'Fixing up something',
            },
            {
                # The second commit on the branch to squash
                'type': 'trivial',
                'summary': 'Fixing up something else',
            },
            {
                # The commit when squashing all commits
                'type': 'bug',
                'summary': 'final summary',
                'description': 'final description',
                'jira': 'WEB-9999',
            },
        ],
    )

    # Make a commit that all branches will shared
    core.commit(allow_empty=True)

    # Make a branch that we will squash
    utils.shell('git branch test-squash')

    # Now commit against the base branch (i.e. make it diverge)
    core.commit(allow_empty=True)

    # Change branches and do a few more commits that will be squashed
    utils.shell('git checkout test-squash')

    core.commit(allow_empty=True)
    core.commit(allow_empty=True)

    assert core.squash('master', allow_empty=True).returncode == 0

    commits = utils.shell_stdout('git --no-pager log')

    # These commits disappeared when squashing
    assert 'Fixing up something' not in commits
    # First commit against master should be in log
    assert 'first master commit' in commits
    # Squashed commit should be in log
    assert 'final description' in commits
    # The divergent commit should not appear in history
    assert 'wont be seen' not in commits


@pytest.mark.usefixtures('git_tidy_repo')
def test_squash_no_commits(mocker):
    """Tests core.squash with no commits"""
    with pytest.raises(exceptions.NoSquashableCommitsError):
        core.squash('HEAD').returncode


@pytest.mark.usefixtures('git_tidy_repo')
def test_squash_error_rollback(mocker):
    """Tests core.squash rolls back resets on commit error"""
    mocker.patch.object(
        formaldict.Schema,
        'prompt',
        autospec=True,
        side_effect=[
            {
                # The first commit
                'type': 'bug',
                'summary': 'summary',
                'description': 'description',
                'jira': 'WEB-9999',
            },
            # Throw an exception when trying to do the squash commit
            Exception,
        ],
    )

    with open('file_to_commit', 'w+') as f:
        f.write('Hello World')

    utils.shell('git add .')
    assert core.commit().returncode == 0

    # The first squash call throws an unexpected error and rolls back the reset
    with pytest.raises(Exception):
        core.squash('HEAD~1')

    assert utils.shell_stdout('git diff --cached') == ''

    # Make commit return a non-zero exit code on next squash commit
    mocker.patch(
        'tidy.core.commit',
        autospec=True,
        return_value=mocker.Mock(returncode=1),
    )

    # The next squash call has a commit error and rolls back the reset
    assert core.squash('HEAD~1').returncode == 1
    assert utils.shell_stdout('git diff --cached') == ''
