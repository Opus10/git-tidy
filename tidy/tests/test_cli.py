import sys
from unittest import mock

import pytest

from tidy import cli


@pytest.fixture
def mock_exit(mocker):
    yield mocker.patch('sys.exit', autospec=True)


@pytest.fixture
def mock_successful_exit(mock_exit):
    yield
    mock_exit.assert_called_once_with(0)


@pytest.mark.usefixtures('mock_successful_exit')
def test_tidy(mocker, capsys):
    """Test calling git-tidy"""
    mocker.patch.object(sys, 'argv', ['git-tidy'])

    cli.tidy()

    out, _ = capsys.readouterr()
    assert out.startswith('git-tidy ')


@pytest.mark.usefixtures('mock_successful_exit')
def test_tidy_template(mocker, capsys):
    """Test calling git-tidy with the "--template" option"""
    mocker.patch.object(sys, 'argv', ['git-tidy', '--template'])
    patched_commit_template = mocker.patch(
        'tidy.core.commit_template', autospec=True
    )

    cli.tidy()

    patched_commit_template.assert_called_once_with(output=sys.stdout)


@pytest.mark.parametrize(
    'command_args, commit_return_code, expected_commit_call',
    [
        ([], 1, mock.call(no_verify=False, allow_empty=False)),
        (['--allow-empty'], 0, mock.call(no_verify=False, allow_empty=True)),
        (['--no-verify'], 0, mock.call(no_verify=True, allow_empty=False)),
    ],
)
def test_tidy_commit(
    mock_exit, mocker, command_args, commit_return_code, expected_commit_call
):
    """Test calling git-tidy-commit"""
    mocker.patch.object(sys, 'argv', ['git-tidy-commit'] + command_args)
    patched_commit = mocker.patch(
        'tidy.core.commit',
        autospec=True,
        return_value=mocker.Mock(returncode=commit_return_code),
    )

    cli.commit()

    assert patched_commit.call_args_list == [expected_commit_call]
    mock_exit.assert_called_once_with(commit_return_code)


@pytest.mark.parametrize(
    'command_args, lint_is_valid, expected_lint_call, expected_stderr',
    [
        ([], True, mock.call('', any=False), ''),
        (['range', '--any'], True, mock.call('range', any=True), ''),
        (
            ['range', '--any'],
            False,
            mock.call('range', any=True),
            (
                '2 out of 2 commits have failed linting:\n'
                "1: ['error1', 'error2']\n2: ['error3', 'error4']\n"
            ),
        ),
    ],
)
def test_tidy_lint(
    mock_exit,
    mocker,
    capsys,
    command_args,
    lint_is_valid,
    expected_lint_call,
    expected_stderr,
):
    """Test calling git-tidy-lint"""
    mocker.patch.object(sys, 'argv', ['git-tidy-lint'] + command_args)
    commits = mocker.MagicMock(
        __len__=lambda a: 2,
        filter=lambda a, b: [
            mocker.Mock(sha=1, validation_errors=['error1', 'error2']),
            mocker.Mock(sha=2, validation_errors=['error3', 'error4']),
        ],
    )
    patched_lint = mocker.patch(
        'tidy.core.lint', autospec=True, return_value=(lint_is_valid, commits)
    )

    cli.lint()

    _, err = capsys.readouterr()
    assert patched_lint.call_args_list == [expected_lint_call]
    mock_exit.assert_called_once_with(0 if lint_is_valid else 1)
    assert err == expected_stderr


@pytest.mark.parametrize(
    'command_args, expected_log_call',
    [
        (  # Verify default parameters are filled out
            [],
            mock.call(
                '',
                style='default',
                tag_match=None,
                before=None,
                after=None,
                reverse=False,
                output=sys.stdout,
            ),
        ),
        (  # Verify default parameters are filled out
            [
                'range',
                '--style=new',
                '--tag-match=pattern',
                '--before=before',
                '--after=after',
                '--reverse',
                '-o',
                'file',
            ],
            mock.call(
                'range',
                style='new',
                tag_match='pattern',
                before='before',
                after='after',
                reverse=True,
                output='file',
            ),
        ),
    ],
)
@pytest.mark.usefixtures('mock_successful_exit')
def test_tidy_log(mocker, command_args, expected_log_call):
    """Test calling git-tidy-log"""
    mocker.patch.object(sys, 'argv', ['git-tidy-log'] + command_args)
    patched_commit = mocker.patch('tidy.core.log', autospec=True)

    cli.log()

    assert patched_commit.call_args_list == [expected_log_call]


@pytest.mark.parametrize(
    'command_args, squash_return_code, expected_squash_call',
    [
        (['ref'], 1, mock.call('ref', no_verify=False, allow_empty=False)),
        (
            ['ref', '--allow-empty'],
            0,
            mock.call('ref', no_verify=False, allow_empty=True),
        ),
        (
            ['ref', '--no-verify'],
            0,
            mock.call('ref', no_verify=True, allow_empty=False),
        ),
    ],
)
def test_tidy_squash(
    mock_exit, mocker, command_args, squash_return_code, expected_squash_call
):
    """Test calling git-tidy-squash"""
    mocker.patch.object(sys, 'argv', ['git-tidy-squash'] + command_args)
    patched_squash = mocker.patch(
        'tidy.core.squash',
        autospec=True,
        return_value=mocker.Mock(returncode=squash_return_code),
    )

    cli.squash()

    assert patched_squash.call_args_list == [expected_squash_call]
    mock_exit.assert_called_once_with(squash_return_code)
