"""Tests for the tidy.github module"""
from contextlib import ExitStack as does_not_raise
import json
from unittest import mock

import pytest
import requests

from tidy import exceptions
from tidy import github


@pytest.fixture(autouse=True)
def setup_github_env_vars(monkeypatch):
    monkeypatch.setenv('GITHUB_API_TOKEN', 'github_token')


@pytest.mark.parametrize(
    'git_origin, expected_org_name, expected_repo_name, expected_exception',
    [
        (
            'git@github.com:jyveapp/random-repo.git',
            'jyveapp',
            'random-repo',
            does_not_raise(),
        ),
        ('', None, None, pytest.raises(exceptions.GithubConfigurationError)),
    ],
)
def test_get_org_and_repo_name(
    mocker,
    git_origin,
    expected_org_name,
    expected_repo_name,
    expected_exception,
):
    """Tests github.get_org_and_repo_name()"""
    mocker.patch(
        'tidy.utils.shell_stdout', return_value=git_origin, autospec=True
    )
    with expected_exception:
        org_name, repo_name = github.get_org_and_repo_name()
        assert org_name == expected_org_name
        assert repo_name == expected_repo_name


@pytest.mark.parametrize(
    'environment, expected_exception',
    [
        (  # Initialization fails without GITHUB_API_TOKEN
            {},
            pytest.raises(exceptions.GithubConfigurationError),
        ),
        ({'GITHUB_API_TOKEN': 'token'}, does_not_raise()),
    ],
)
def test_github_client_init(environment, expected_exception, mocker):
    """Tests initialization of GithubClient()"""
    mocker.patch.dict('os.environ', environment, clear=True)
    with expected_exception:
        github.GithubClient()


def test_github_client_call_api(mocker, responses):
    """Tests GithubClient._call_api()"""
    responses.add(responses.POST, 'https://api.github.com/url/base')

    c = github.GithubClient()
    c._call_api(
        'post',
        '/url/base',
        headers={'additonal': 'header'},
        data={'post': 'data'},
    )

    assert len(responses.calls) == 1
    assert responses.calls[0].request.body == 'post=data'
    assert responses.calls[0].request.headers['additonal'] == 'header'
    assert (
        responses.calls[0].request.headers['Authorization']
        == 'token github_token'
    )


def test_github_client_get_patch_post(mocker):
    """Tests GithubClient.get(), patch(), and post() utility methods"""
    patched_call_api = mocker.patch.object(
        github.GithubClient, '_call_api', autospec=True
    )
    c = github.GithubClient()
    c.get('/get/url', get_arg='get')
    c.patch('/patch/url', patch_arg='patch')
    c.post('/post/url', post_arg='post')

    assert patched_call_api.call_args_list == [
        mocker.call(mocker.ANY, 'get', '/get/url', get_arg='get'),
        mocker.call(mocker.ANY, 'patch', '/patch/url', patch_arg='patch'),
        mocker.call(mocker.ANY, 'post', '/post/url', post_arg='post'),
    ]


@pytest.mark.parametrize(
    'api_status, api_return, expected_pr, expected_exception',
    [
        (  # When an unexpected Github API error happens
            500,
            None,
            None,
            pytest.raises(exceptions.GithubPullRequestAPIError),
        ),
        (  # When there are no pull requests
            200,
            [],
            None,
            pytest.raises(exceptions.NoGithubPullRequestFoundError),
        ),
        (  # An error is raised if there are multiple pull requests
            200,
            [{}, {}],
            None,
            pytest.raises(exceptions.MultipleGithubPullRequestsFoundError),
        ),
        (200, [{'pr': 'payload'}], {'pr': 'payload'}, does_not_raise()),
    ],
)
def test_get_pull_request(
    mocker, responses, api_return, api_status, expected_pr, expected_exception
):
    """Tests github.get_pull_request()"""
    mocker.patch(
        'tidy.utils.shell_stdout',
        autospec=True,
        side_effect=[
            # The first shell call gets the git remote branch
            'git@github.com:jyveapp/random-repo.git',
            # The second shell call gets the current git branch
            'current_branch',
        ],
    )
    responses.add(
        responses.GET,
        (
            'https://api.github.com/repos/jyveapp/random-repo/'
            'pulls?head=jyveapp:current_branch'
        ),
        json=api_return,
        status=api_status,
    )

    with expected_exception:
        assert github.get_pull_request() == expected_pr


def test_get_pull_request_base(mocker):
    """Tests github.get_pull_request_base()"""
    mocker.patch(
        'tidy.github.get_pull_request',
        autospec=True,
        return_value={'base': {'ref': 'base_branch'}},
    )

    assert github.get_pull_request_base() == 'origin/base_branch'


@pytest.mark.parametrize(
    'github_username, pr, pr_comments, expected_client_calls, expected_exception',
    [
        (  # A github username must be configured
            '',
            {'number': 10},
            None,
            None,
            pytest.raises(exceptions.GithubConfigurationError),
        ),
        (  # New PR comments post a new comment message
            'user',
            {'number': 10},
            [{'user': {'login': 'another_user'}}],
            [
                mock.call(
                    mock.ANY,
                    'get',
                    '/repos/org_name/repo_name/issues/10/comments',
                ),
                mock.call(
                    mock.ANY,
                    'post',
                    '/repos/org_name/repo_name/issues/10/comments',
                    json={'body': 'message'},
                ),
            ],
            does_not_raise(),
        ),
        (  # The comment is patched if it already exists
            'user',
            {'number': 10},
            [{'id': 110, 'user': {'login': 'user'}}],
            [
                mock.call(
                    mock.ANY,
                    'get',
                    '/repos/org_name/repo_name/issues/10/comments',
                ),
                mock.call(
                    mock.ANY,
                    'patch',
                    '/repos/org_name/repo_name/issues/comments/110',
                    json={'body': 'message'},
                ),
            ],
            does_not_raise(),
        ),
    ],
)
def test_comment(
    mocker,
    monkeypatch,
    github_username,
    pr,
    pr_comments,
    expected_client_calls,
    expected_exception,
):
    """Tests github.comment()"""
    comment_response = requests.Response()
    comment_response._content = json.dumps(pr_comments).encode()
    patched_client_call = mocker.patch.object(
        github.GithubClient,
        '_call_api',
        autospec=True,
        side_effect=[comment_response, None],
    )
    monkeypatch.setenv('GITHUB_USERNAME', github_username)
    mocker.patch(
        'tidy.github.get_pull_request', autospec=True, return_value=pr
    )
    mocker.patch(
        'tidy.github.get_org_and_repo_name',
        autospec=True,
        return_value=('org_name', 'repo_name'),
    )

    with expected_exception:
        github.comment('message')

        assert patched_client_call.call_args_list == expected_client_calls
