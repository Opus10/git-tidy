"""
Utilities for git tidy
"""

import os
import subprocess


def shell(cmd, check=True, stdin=None, stdout=None, stderr=None):
    """Runs a subprocess shell with check=True by default"""
    return subprocess.run(
        cmd, shell=True, check=check, stdin=stdin, stdout=stdout, stderr=stderr
    )


def shell_stdout(cmd, check=True, stdin=None, stderr=None):
    """Runs a shell command and returns stdout"""
    ret = shell(
        cmd, stdout=subprocess.PIPE, check=check, stdin=stdin, stderr=stderr
    )
    return ret.stdout.decode('utf-8').strip() if ret.stdout else ''


def get_tidy_file_root():
    """
    Get the root path of tidy files
    """
    top_level = shell_stdout('git rev-parse --show-toplevel')
    return os.path.join(top_level, '.git-tidy')


def get_tidy_file_path(name):
    """
    Load a tidy file path.

    Determines the path based on the git root folder
    joined with ".git-tidy/{name}"
    """
    return os.path.join(get_tidy_file_root(), name)
