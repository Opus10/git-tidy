"""Tests the tidy.core module

Most of the test coverage of the core module is from the integration
tests in tidy/tests/test_integration.py.
"""
from contextlib import ExitStack as does_not_raise
from unittest import mock

import pytest

from tidy import core
from tidy import exceptions


# A user schema that overrides the default git tidy schema
overridden_user_schema = '''
- label: type
- label: summary
- label: description
  condition: ['!=', 'type', 'trivial']
  multiline: True
  required: False
 '''

# A user schema that has no overrides on the default tidy schema
nonoverridden_user_schema = '- label: type'

# An invalid user schema
invalid_user_schema = '- invalid: type'

# An invalid user schema - multiline input can only be used for description
invalid_multiline_user_schema = '''
- label: type
- label: summary
- label: stuff
  multiline: True
 '''


@pytest.mark.parametrize(
    'user_schema, full, expected_exception, expected_schema_labels',
    [
        (
            overridden_user_schema,
            True,
            does_not_raise(),
            [
                'sha',
                'author_name',
                'author_email',
                'author_date',
                'committer_name',
                'committer_email',
                'committer_date',
                'type',
                'summary',
                'description',
            ],
        ),
        (
            nonoverridden_user_schema,
            False,
            does_not_raise(),
            ['summary', 'description', 'type'],
        ),
        (None, False, does_not_raise(), ['summary', 'description']),
        (
            invalid_user_schema,
            None,
            pytest.raises(exceptions.SchemaError),
            None,
        ),
        (
            invalid_multiline_user_schema,
            None,
            pytest.raises(exceptions.SchemaError),
            None,
        ),
    ],
)
def test_load_commit_schema(
    tmp_path,
    mocker,
    user_schema,
    full,
    expected_exception,
    expected_schema_labels,
):
    """Tests core._load_commit_schema()"""
    user_schema_file = tmp_path / 'commit.yaml'
    if user_schema:
        user_schema_file.write_text(user_schema)

    with expected_exception:
        schema = core._load_commit_schema(path=user_schema_file, full=full)
        assert [s['label'] for s in schema] == expected_schema_labels


@pytest.mark.parametrize(
    'git_version, expected_exception',
    [
        ('2.22.0', does_not_raise()),
        ('2.22.1', does_not_raise()),
        ('2.23', does_not_raise()),
        ('1.1', pytest.raises(RuntimeError)),
    ],
)
def test_check_git_version(mocker, git_version, expected_exception):
    """Tests core._check_git_version"""
    mocker.patch(
        'tidy.utils.shell_stdout', autospec=True, return_value=git_version
    )
    with expected_exception:
        core._check_git_version()


@pytest.mark.parametrize(
    'key, value, expected_return',
    [
        ('key', 1, 1),
        ('key', '1', '1'),
        (
            'trailers',
            [{' Trailer-One ': ' v1 '}, {'Trailer-Two': 'v2 '}],
            {'trailer_one': 'v1', 'trailer_two': 'v2'},
        ),
        (
            'description',
            'Description\n\nHas-Trailers: At\nThe-Bottom: Of It',
            'Description',
        ),
        (
            'description',
            '\nThis Description\n\nDoes not have trailers: in it\n\n',
            'This Description\n\nDoes not have trailers: in it',
        ),
    ],
)
def test_format_commit_attr(mocker, key, value, expected_return):
    """Tests core._format_commit_attr()"""
    assert core._format_commit_attr(key, value) == expected_return


@pytest.mark.parametrize(
    'sha, tag_match, git_describe_output, expected_git_call, expected_tag_value',
    [
        ('sha1', None, '0.1~8', 'git describe sha1 --contains', '0.1'),
        (
            'sha1',
            'pattern',
            '',
            'git describe sha1 --contains --match=pattern',
            'None',
        ),
    ],
)
def test_tag_from_sha(
    mocker,
    sha,
    tag_match,
    git_describe_output,
    expected_git_call,
    expected_tag_value,
):
    """Tests core.Tag.from_sha()"""
    patched_describe = mocker.patch(
        'tidy.utils.shell_stdout',
        autospec=True,
        return_value=git_describe_output,
    )

    assert (
        str(core.Tag.from_sha(sha, tag_match=tag_match)) == expected_tag_value
    )
    assert patched_describe.call_args_list[0][0][0] == expected_git_call


@pytest.mark.parametrize(
    'git_log_output, expected_git_log_call, expected_date',
    [('', mock.call('git log -1 --format=%ad 2.1'), None)],
)
def test_tag_date(
    mocker, git_log_output, expected_git_log_call, expected_date
):
    """Tests core.Tag.date()"""
    patched_shell = mocker.patch(
        'tidy.utils.shell_stdout', autospec=True, return_value=git_log_output
    )
    tag = core.Tag('2.1')

    assert tag.date == expected_date
    assert tag.date == expected_date  # Run twice to exercise caching
    assert patched_shell.call_args_list == [expected_git_log_call]


def test_get_pull_request_range(mocker):
    """Tests core._get_pull_request_range"""
    mocker.patch(
        'tidy.github.get_pull_request_base',
        autospec=True,
        return_value='develop',
    )
    assert core._get_pull_request_range() == 'develop..'
