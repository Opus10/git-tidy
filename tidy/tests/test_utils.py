"""Tests the tidy.utils() module"""
from tidy import utils


def test_shell_stdout():
    """Tests utils.shell_stdout()"""
    assert utils.shell_stdout('echo "hello world"') == 'hello world'


def test_get_tidy_file_root(mocker):
    """Tests utils.get_tidy_file_root()"""
    mocker.patch(
        'tidy.utils.shell_stdout',
        autospec=True,
        # Return value for "git rev-parse --show-toplevel" call
        return_value='/work/git-tidy',
    )

    assert utils.get_tidy_file_root() == '/work/git-tidy/.git-tidy'


def test_get_tidy_file_path(mocker):
    """Tests utils.get_tidy_file_path()"""
    mocker.patch(
        'tidy.utils.get_tidy_file_root',
        autospec=True,
        return_value='/tidy/root',
    )
    assert utils.get_tidy_file_path('name') == '/tidy/root/name'
