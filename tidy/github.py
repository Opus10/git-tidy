"""
Utilities for accessing Github
"""

import os

import requests

from tidy import exceptions
from tidy import utils


GITHUB_API_TOKEN_ENV_VAR = 'GITHUB_API_TOKEN'
GITHUB_USERNAME_ENV_VAR = 'GITHUB_USERNAME'


def get_org_and_repo_name():
    remote_url = utils.shell_stdout('git remote get-url origin')
    if not remote_url:
        raise exceptions.GithubConfigurationError(
            'Must have a remote named "origin" in order to work with Github.'
        )

    org_name, repo_name = remote_url.split(':')[1].split('/')

    assert repo_name.endswith('.git')
    return org_name, repo_name[0:-4]


class GithubClient:
    """Utility client for accessing Github API"""

    def __init__(self):
        if not os.environ.get(GITHUB_API_TOKEN_ENV_VAR):  # pragma: no cover
            raise exceptions.GithubConfigurationError(
                f'Must set the "{GITHUB_API_TOKEN_ENV_VAR}" environment'
                ' variable for Github access.'
            )

        self.api_token = os.environ[GITHUB_API_TOKEN_ENV_VAR]

    def _call_api(self, verb, url, **request_kwargs):
        """Perform a github API call

        Args:
            verb (str): Can be "post", "put", or "get"
            url (str): The base URL with a leading slash for Github API (v3)
        """
        api = 'https://api.github.com{}'.format(url)
        auth_headers = {'Authorization': 'token {}'.format(self.api_token)}
        headers = {**auth_headers, **request_kwargs.pop('headers', {})}
        resp = getattr(requests, verb)(api, headers=headers, **request_kwargs)
        resp.raise_for_status()
        return resp

    def get(self, url, **request_kwargs):
        """Github API get"""
        return self._call_api('get', url, **request_kwargs)

    def post(self, url, **request_kwargs):
        """Github API post"""
        return self._call_api('post', url, **request_kwargs)

    def patch(self, url, **request_kwargs):
        """Github API put"""
        return self._call_api('patch', url, **request_kwargs)


def get_pull_request():
    """Find the pull request in github

    Raises:
        NoPullRequestFoundError: If a pull request isn't found
        MultiplePullRequestsFoundError: If multiple pull requests are
            opened from the current branch
    """
    org_name, repo_name = get_org_and_repo_name()
    current_branch = utils.shell_stdout(
        "git --no-pager branch | grep \\* | cut -d ' ' -f2"
    )

    try:
        prs = (
            GithubClient()
            .get(
                f'/repos/{org_name}/{repo_name}/pulls'
                f'?head={org_name}:{current_branch}'
            )
            .json()
        )
    except requests.exceptions.RequestException as exc:
        raise exceptions.GithubPullRequestAPIError(
            'An unexpected error occurred with the Github pull requests'
            ' API.'
        ) from exc

    if not prs:
        raise exceptions.NoGithubPullRequestFoundError(
            f'No pull requests found for branch "{current_branch}"'
        )

    if len(prs) > 1:
        raise exceptions.MultipleGithubPullRequestsFoundError(
            f'Multiple pull requests found for branch "{current_branch}"'
        )

    return prs[0]


def get_pull_request_base(pr=None):
    """Find the pull request base branch in github

    Raises:
        NoPullRequestFoundError: If a pull request isn't found
        MultiplePullRequestsFoundError: If multiple pull requests are
            opened from the current branch
    """
    pr = pr or get_pull_request()
    return f"origin/{pr['base']['ref']}"


def comment(message):
    """
    Comment a message on a pull request
    """
    pr = get_pull_request()
    pr_number = pr['number']

    org_name, repo_name = get_org_and_repo_name()
    github_username = os.environ.get(GITHUB_USERNAME_ENV_VAR)
    if not github_username:
        raise exceptions.GithubConfigurationError(
            f'Must set "{GITHUB_USERNAME_ENV_VAR}" in order to post comments'
            ' as a specific user.'
        )

    # Try to find a comment already created so that it can be edited
    pr_comments_url = (
        f'/repos/{org_name}/{repo_name}/issues/{pr_number}/comments'
    )
    pr_comments = GithubClient().get(pr_comments_url).json()
    pr_comment_id = None
    for pr_comment in pr_comments:
        if pr_comment['user']['login'] == github_username:
            pr_comment_id = pr_comment['id']

    if pr_comment_id:
        comment_edit_url = (
            f'/repos/{org_name}/{repo_name}/issues/comments/{pr_comment_id}'
        )
        GithubClient().patch(comment_edit_url, json={'body': message})
    else:
        GithubClient().post(pr_comments_url, json={'body': message})
