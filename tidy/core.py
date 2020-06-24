"""
The core git tidy API
"""

import collections.abc
import io
import os
import re
import subprocess
import tempfile

import dateutil.parser
import formaldict
import jinja2
from packaging import version
import yaml

from tidy import exceptions
from tidy import github
from tidy import utils


# The default tidy log Jinja template
DEFAULT_LOG_TEMPLATE = """
{% for tag, commits_by_tag in commits.group('tag').items() %}
## {{ tag|default('Unreleased', True) }} {% if tag.date %}({{ tag.date.date() }}){% endif %}
{% for commit in commits_by_tag %}
- {{ commit.summary }} [{{ commit.author_name }}, {{ commit.sha[:7] }}]
{% if commit.description %}

    {{ commit.description|indent(4) }}
{% endif %}
{% endfor %}

{% endfor %}
"""
# Used for parsing descriptions from git commits and excluding trailers
REGEX_RFC822_POSTFIX = (
    r'((^|\n)(?P<key>[A-Z]\w+(-\w+)*):(?P<value>[^\n]*(\n\s+[^\n]*)*))+$'
)
# The special range value for git ranges against github pull requests
GITHUB_PR = ':github/pr'


def _output(*, value, path):
    """
    Outputs a value to a path.

    Args:
        value (str): The string to output.
        path (str|file): The path to which output is stored. If
            given a string, the value will be stored to the path referenced
            by the string. If ":github/pr" is the path, the value will be
            written as a Github pull request comment. If the path is anything
            but a string, it is treated as a file-like object. If path is
            ``None``, nothing is written.
    """
    if isinstance(path, str) and path != GITHUB_PR:
        with open(path, 'w+') as f:
            f.write(value)
    elif isinstance(path, str) and path == GITHUB_PR:
        github.comment(value)
    elif path is not None:
        path.write(value)
        path.flush()


def _load_commit_schema(path=None, full=True):
    """Loads the tidy schema

    By default, a subject and optional description are needed
    when performing a tidy commit. Other attributes of a commit
    are needed when linting/logging the commits
    """
    path = path or utils.get_tidy_file_path('commit.yaml')

    default_schema = [
        {
            'label': 'summary',
            'name': 'Summary',
            'help': 'A high-level summary of the commit.',
            'type': 'string',
        },
        {
            'label': 'description',
            'name': 'Description',
            'help': 'An in-depth description of the changes.',
            'type': 'string',
            'multiline': True,
            'required': False,
        },
    ]

    if full:
        default_schema += [
            {
                'label': 'sha',
                'name': 'SHA',
                'help': 'Full SHA of the commit.',
                'type': 'string',
            },
            {
                'label': 'author_name',
                'name': 'Author Name',
                'help': 'The author name of the commit.',
                'type': 'string',
            },
            {
                'label': 'author_email',
                'name': 'Author Email',
                'help': 'The author email of the commit.',
                'type': 'string',
            },
            {
                'label': 'author_date',
                'name': 'Author Date',
                'help': 'The time at which the commit was authored.',
                'type': 'datetime',
            },
            {
                'label': 'committer_name',
                'name': 'Committer Name',
                'help': 'The name of the person who performed the commit.',
                'type': 'string',
            },
            {
                'label': 'committer_email',
                'name': 'Committer Email',
                'help': 'The email of the person who performed the commit.',
                'type': 'string',
            },
            {
                'label': 'committer_date',
                'name': 'Committer Date',
                'help': 'The time at which the commit was performed.',
                'type': 'datetime',
            },
        ]

    try:
        with open(path, 'r') as schema_f:
            user_schema = yaml.safe_load(schema_f)
    except IOError:
        user_schema = []

    for entry_schema in user_schema:
        if 'label' not in entry_schema:
            raise exceptions.SchemaError(
                f'Entry in schema does not have label - {entry_schema}'
            )
        elif (
            entry_schema.get('multiline')
            and entry_schema['label'] != 'description'
        ):
            raise exceptions.SchemaError(
                'Invalid schema for entry with label'
                f' "{entry_schema["label"]}". Multi-line'
                ' input is only allowed for the commit description.'
            )

    user_labels = {entry_schema['label'] for entry_schema in user_schema}
    schema = [
        entry_schema
        for entry_schema in default_schema
        if entry_schema['label'] not in user_labels
    ] + user_schema

    return formaldict.Schema(schema)


def _check_git_version():
    """Verify git version"""
    git_version = utils.shell_stdout(
        "git --version | rev | cut -f 1 -d' ' | rev"
    )
    if version.parse(git_version) < version.parse('2.22.0'):
        raise RuntimeError(
            f'Must have git version >= 2.22.0 (version = {git_version})'
        )


def _format_commit_attr(key, value):
    """
    After parsing commits into yaml, format the values of the parsed
    key/value pairs
    """
    if key == 'trailers':
        value = {
            trailer_key.strip()
            .lower()
            .replace('-', '_'): trailer_value.strip()
            for trailer in value
            for trailer_key, trailer_value in trailer.items()
        }
    elif key == 'description':
        # Remove trailers from the description
        match = re.search(REGEX_RFC822_POSTFIX, value)
        if match is not None:
            description_end = match.start()
            value = value[:description_end].strip()

    if key != 'trailers' and isinstance(value, str):
        value = value.strip()

    return value


class Tag(collections.UserString):
    """A git tag."""

    def __init__(self, tag):
        self.data = tag

    @classmethod
    def from_sha(cls, sha, tag_match=None):
        """
        Create a Tag object from a sha or return None if there is no
        associated tag

        Returns:
            Tag: A constructed tag or ``None`` if no tags contain the commit.
        """
        describe_cmd = f'git describe {sha} --contains'
        if tag_match:
            describe_cmd += f' --match={tag_match}'

        rev = (
            utils.shell_stdout(
                describe_cmd, check=False, stderr=subprocess.PIPE
            )
            .replace('~', ':')
            .replace('^', ':')
        )
        return cls(rev.split(':')[0]) if rev else None

    @property
    def date(self):
        """
        Parse the date of the tag

        Returns:
            datetime: The tag parsed as a datetime object.
        """
        if not hasattr(self, '_date'):
            try:
                self._date = dateutil.parser.parse(
                    utils.shell_stdout(f'git log -1 --format=%ad {self}')
                )
            except dateutil.parser.ParserError:
                self._date = None

        return self._date


class Commit(collections.UserString):
    """
    Parses a commit message into structured components.

    It is assumed the commit message is formatted as YAML by
    the appropriate "git log" command (see `CommitRange`).
    If data is able to be parsed, attributes of the commit
    can be accessed as attributes of this object. For example, a
    ``type`` attribute in the schema is accessible as
    ``Commit().type``.

    If the commit cannot be parsed as valid YAML for unexpected
    reasons, ``is_parsed`` is ``False`` and only a limited amount of
    attributes are available.
    """

    def __init__(self, msg, schema, tag_match=None):
        msg = msg.strip()

        self._schema = schema
        self.data = msg
        self._tag_match = tag_match

        try:
            commit_data = yaml.safe_load(io.StringIO(msg))

            # Format commit attributes
            commit_data = {
                key: _format_commit_attr(key, value)
                for key, value in commit_data.items()
            }

            # Flatten attributes
            commit_data = {
                **{k: v for k, v in commit_data.items() if k != 'trailers'},
                **commit_data['trailers'],
            }

            # Parse the commit data
            self.schema_data = schema.parse(commit_data)
            self._is_parsed = True
        except Exception as exc:
            # If the yaml data cannot be parsed, construct a special
            # formal dictionary object with an appropriate error
            match = re.match(r'sha: (?P<sha>[a-fA-F\d]+)\n', msg)
            sha = match.group('sha')
            errors = formaldict.Errors()
            errors.add(exceptions.CommitParseError(str(exc)))

            self.schema_data = formaldict.FormalDict(
                schema=schema,
                parsed={'sha': sha},
                data={'sha': sha},
                errors=errors,
            )
            self._is_parsed = False

    def __getattribute__(self, attr):
        try:
            return object.__getattribute__(self, attr)
        except AttributeError:
            if self.schema_data and attr in self.schema_data:
                return self.schema_data[attr]
            elif attr in self._schema:
                return None
            else:
                raise

    @property
    def is_parsed(self):
        """``True`` if the commit has been parsed successfully.

        If ``False``, only the ``sha`` and ``msg`` attributes
        are available.
        """
        return self._is_parsed

    @property
    def is_valid(self):
        """
        ``True`` if the commit was successfully validated against
        the schema. If ``False``, some attributes in the schema may
        be missing.
        """
        return self.schema_data.is_valid

    @property
    def validation_errors(self):
        """
        Returns the schema ``formaldict.Errors`` that occurred during
        validation
        """
        return self.schema_data.errors

    @property
    def msg(self):
        """The raw git commit message"""
        return self.data

    @property
    def tag(self):
        """Returns a `Tag` that contains the commit"""
        if not hasattr(self, '_tag'):
            self._tag = Tag.from_sha(self.sha, tag_match=self._tag_match)

        return self._tag


def _equals(a, b, match=False):
    """True if a equals b. If match is True, perform a regex match

    If b is a regex ``Pattern``, applies regex matching
    """
    if match:
        return re.match(b, a) is not None if isinstance(a, str) else False
    else:
        return a == b


class Commits(collections.abc.Sequence):
    """A filterable and groupable collection of commits

    When a list of Commit objects is organized in this sequence, the
    "group", "filter", and "exclude" chainable methods can be used
    for various access patterns. These access patterns are typically
    used when writing git tidy log templates.
    """

    def __init__(self, commits):
        self._commits = commits

    def __getitem__(self, i):
        return self._commits[i]

    def __len__(self):
        return len(self._commits)

    def filter(self, attr, value, match=False):
        """Filter commits by an attribute

        Args:
            attr (str): The name of the attribute on the `Commit` object.
            value (str|bool): The value to filter by.
            match (bool, default=False): Treat ``value`` as a regex pattern and
                match against it.

        Returns:
            `Commits`: The filtered commits.
        """
        return Commits(
            [
                commit
                for commit in self
                if _equals(getattr(commit, attr), value, match=match)
            ]
        )

    def exclude(self, attr, value, match=False):
        """Exclude commits by an attribute

        Args:
            attr (str): The name of the attribute on the `Commit` object.
            value (str|bool): The value to exclude by.
            match (bool, default=False): Treat ``value`` as a regex pattern and
                match against it.

        Returns:
            `Commits`: The excluded commits.
        """
        return Commits(
            [
                commit
                for commit in self
                if not _equals(getattr(commit, attr), value, match=match)
            ]
        )

    def group(
        self,
        attr,
        ascending_keys=False,
        descending_keys=False,
        none_key_first=False,
        none_key_last=False,
    ):
        """Group commits by an attribute

        Args:
            attr (str): The attribute to group by.
            ascending_keys (bool, default=False): Sort the keys in ascending
                order.
            descending_keys (bool, default=False): Sort the keys in descending
                order.
            none_key_first (bool, default=False): Make the "None" key be first.
            none_key_last (bool, default=False): Make the "None" key be last.

        Returns:
            `collections.OrderedDict`: A dictionary of `Commits` keyed on
            groups.
        """
        if any([ascending_keys, descending_keys]) and not any(
            [none_key_first, none_key_last]
        ):
            # If keys are sorted, default to making the "None" key last
            none_key_last = True

        # Get the natural ordering of the keys
        keys = list(
            collections.OrderedDict(
                (getattr(commit, attr), True) for commit in self
            ).keys()
        )

        # Re-sort the keys
        if any([ascending_keys, descending_keys]):
            sorted_keys = sorted(
                (k for k in keys if k is not None), reverse=descending_keys
            )
            if None in keys:
                sorted_keys.append(None)

            keys = sorted_keys

        # Change the ordering of the "None" key
        if any([none_key_first, none_key_last]) and None in keys:
            keys.remove(None)
            keys.insert(0 if none_key_first else len(keys), None)

        return collections.OrderedDict(
            (key, self.filter(attr, key)) for key in keys
        )


def _get_pull_request_range():
    base = github.get_pull_request_base()
    return f'{base}..'


def _git_log_as_yaml(git_log_cmd):
    """
    Outputs git log in a format parseable as YAML.

    Args:
        git_log_cmd (str): The primary "git log .." command.
            This function adds the "--format" parameter to
            it and cleans the resulting log.

    Returns:
        List[str]: The "git log" return value where every line can
        be parsed as YAML.
    """
    # NOTE(@wesleykendall) - The git log is rendered as YAML so that it
    # can be parsed as key/value pairs. There are some circumstances
    # that are not fixed where the log cannot be parsed as YAML
    # (e.g. having a trailer value start with a ":"). git-tidy still
    # provides the ability to filter unparsed commits.
    #
    # We assume the parsed commit always has the following keys:
    # sha: The full commit sha (%H). Must always be rendered first
    # author_name: The author name (%an)
    # author_email: The author email (%ae)
    delimiter = '\n<-------->'
    git_log_stdout = utils.shell_stdout(
        f'{git_log_cmd} '
        '--format="'
        'sha: %H%n'
        'author_name: %an%n'
        'author_email: %ae%n'
        'author_date: %ad%n'
        'committer_name: %cn%n'
        'committer_email: %ce%n'
        'committer_date: %cd%n'
        'summary: |%n%w(0, 4, 4)%s%n%w(0, 0, 0)'
        'description: |%n%w(0, 4, 4)%b%n%w(0, 0, 0)'
        'trailers: [*{*%(trailers:separator=*%x7d*%x2c*%x7b*)*}*]'
        f'%n{delimiter}"'
    )

    # Escape any double quotes used in trailers
    git_log_stdout = re.sub(
        r'^trailers:.*$',
        lambda x: x.group().replace('"', r'\"'),
        git_log_stdout,
        flags=re.MULTILINE,
    )
    # Format all empty trailer dictionaries. This only happens when
    # there are no trailers
    git_log_stdout = re.sub(r'\*{\*\*}\*', r'{}', git_log_stdout)

    # Quote all trailer values
    git_log_stdout = re.sub(r'\*{\*(\w+: )', r'{\1"', git_log_stdout)
    git_log_stdout = re.sub(r'\*}\*', r'"}', git_log_stdout)

    return [msg for msg in git_log_stdout.split(delimiter) if msg]


class CommitRange(Commits):
    """
    Represents a range of commits. The commit range can be filtered and grouped
    using all of the methods in `Commits`.

    When doing ``git log``, the user can provide a range
    (e.g. "origin/develop.."). Any range used in "git log" can be
    used as a range to the CommitRange object.

    If the special ``:github/pr`` value is used as a range, the Github
    API is used to figure out the range based on a pull request opened
    from the current branch (if found).
    """

    def __init__(
        self, range='', tag_match=None, before=None, after=None, reverse=False
    ):
        self._schema = _load_commit_schema()
        self._tag_match = tag_match
        self._before = before
        self._after = after
        self._reverse = reverse
        _check_git_version()

        # The special ":github/pr" range will do a range against the base
        # pull request branch
        if range == GITHUB_PR:
            range = _get_pull_request_range()

        # Ensure any remotes are fetched
        utils.shell('git --no-pager fetch -q')

        git_log_cmd = f'git --no-pager log {range} --no-merges'
        if before:
            git_log_cmd += f' --before={before}'
        if after:
            git_log_cmd += f' --after={after}'
        if reverse:
            git_log_cmd += f' --reverse'

        git_yaml_logs = _git_log_as_yaml(git_log_cmd)

        self._range = range

        return super().__init__(
            [
                Commit(msg, self._schema, tag_match=self._tag_match)
                for msg in git_yaml_logs
            ]
        )


def commit_template(output=None):
    """Returns the template for a tidy commit.

    The template can be stored to a file and configured to be the
    template for every standard ``git commit``. For example::

        git tidy --template >> .commit.tpl
        git config --local commit.template .commit.tpl

    Args:
        output (str|file): Path or file-like object to which the template is
            written.
    """
    schema = _load_commit_schema(full=False)
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(utils.get_tidy_file_root()),
        trim_blocks=True,
    )
    template = env.get_template('commit.tpl')
    rendered = template.render(schema=schema)

    _output(path=output, value=rendered)

    return rendered


def commit(no_verify=False, allow_empty=False, defaults=None):
    """
    Performs a tidy git commit.

    Args:
        no_verify (bool, default=False): True if ignoring
            pre-commit hooks
        allow_empty (bool, default=False): True if an empty
            commit should be allowed
        defaults (dict, default=None): Defaults to be used
            when prompting for commit attributes.

    Returns:
        subprocess.CompletedProcess: The result from running
        git commit. Returns the git pre-commit hook results if
        failing during hook execution.
    """
    # Run pre-commit hooks manually so that the commit will fail
    # before prompting the user for information
    hooks_path = utils.shell_stdout('git rev-parse --git-path hooks')
    pre_commit_hook = os.path.join(hooks_path, 'pre-commit')
    if not no_verify and os.path.exists(pre_commit_hook):
        result = utils.shell(pre_commit_hook, check=False)
        if result.returncode:
            return result

    # If there are no staged changes and we are not allowing empty
    # commits (the default git commit mode), short circuit and run
    # a failing git commit
    staged_changes = utils.shell_stdout('git diff --cached')
    if not staged_changes and not allow_empty:
        return utils.shell(f'git commit --no-verify', check=False)

    schema = _load_commit_schema(full=False)
    entry = schema.prompt(defaults=defaults)

    # Render the commit message from the validated entry
    commit_msg = ''
    if 'summary' in entry:
        commit_msg += f'{entry["summary"].strip()}\n\n'
    if 'description' in entry:
        commit_msg += f'{entry["description"].strip()}\n\n'

    for key, value in entry.items():
        if key not in ['summary', 'description']:
            key = key.replace('_', ' ').title().replace('_', '-').strip()
            commit_msg += f'{key}: {value.strip()}\n'

    commit_msg = commit_msg.strip()

    # Commit with git
    commit_cmd = 'git commit --no-verify'
    if allow_empty:
        commit_cmd += ' --allow-empty'
    with tempfile.NamedTemporaryFile(mode='w+') as commit_file:
        commit_file.write(commit_msg)
        commit_file.flush()

        return utils.shell(f'{commit_cmd} -F {commit_file.name}', check=False)


def lint(range='', any=False):
    """
    Lint commits against an upstream (branch, sha, etc).

    Args:
        range (str, default=''): The git revision range against which linting
            happens. The special value of ":github/pr" can be used to lint
            against the remote branch of the pull request that is opened
            from the local branch. No range means linting will happen against
            all commits.
        any (bool, default=False): If True, linting will pass if at least
            one commit passes.

    Raises:
        `NoGithubPullRequestFoundError`: When using ``:github/pr`` as
            the range and no pull requests are found.
        `MultipleGithubPullRequestsFoundError`: When using ``:github/pr`` as
            the range and multiple pull requests are found.

    Returns:
        tuple(bool, CommitRange): A tuple of the lint result (True/False)
        and the associated CommitRange
    """
    commits = CommitRange(range=range)
    if not any:
        return not commits.filter('is_valid', False), commits
    else:
        return bool(commits.filter('is_valid', True)), commits


def log(
    range='',
    style='default',
    tag_match=None,
    before=None,
    after=None,
    reverse=False,
    output=None,
):
    """
    Renders git logs using tidy rendering.

    Args:
        range (str, default=''): The git revision range over which logs are
            output. Using ":github/pr" as the range will use the base branch
            of an open github pull request as the range. No range will result
            in all commits being logged.
        style (str, default="default"): The template to use when rendering.
            Defaults to "default", which means ``.git-tidy/log.tpl`` will
            be used to render. When used, the ``.git-tidy/log_{{style}}.tpl``
            file will be rendered.
        tag_match (str, default=None): A glob(7) pattern for matching tags
            when associating a tag with a commit in the log. Passed through
            to ``git describe --contains --matches`` when finding a tag.
        before (str, default=None): Only return commits before a specific
            date. Passed directly to ``git log --before``.
        after (str, default=None): Only return commits after a specific
            date. Passed directly to ``git log --after``.
        reverse (bool, default=False): Reverse ordering of results. Passed
            directly to ``git log --reverse``.
        output (str|file): Path or file-like object to which the template is
            written. Using the special ":github/pr" output path will post the
            log as a comment on the pull request.

    Raises:
        `NoGithubPullRequestFoundError`: When using ``:github/pr`` as
            the range and no pull requests are found.
        `MultipleGithubPullRequestsFoundError`: When using ``:github/pr`` as
            the range and multiple pull requests are found.

    Returns:
        str: The rendered tidy log.
    """
    commits = CommitRange(
        range=range,
        tag_match=tag_match,
        before=before,
        after=after,
        reverse=reverse,
    )
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(utils.get_tidy_file_root()),
        trim_blocks=True,
    )
    template_file = 'log.tpl' if style == 'default' else f'log_{style}.tpl'
    try:
        template = env.get_template(template_file)
    except jinja2.exceptions.TemplateNotFound:
        if style == 'default':
            # Use the default tidy template if the user didn't provide one
            template = jinja2.Template(DEFAULT_LOG_TEMPLATE, trim_blocks=True)
        else:
            raise
    rendered = template.render(commits=commits, output=output, range=range)

    _output(path=output, value=rendered)

    return rendered


def squash(ref, no_verify=False, allow_empty=False):
    """
    Squashes all commits since the common ancestor of ref.

    Args:
        ref (str): The git reference to squash against. Every commit after
            the common ancestor of this reference will be squashed.
        no_verify (bool, default=False): True if ignoring
            pre-commit hooks
        allow_empty (bool, default=False): True if an empty
            commit should be allowed

    Raises:
        `NoSquashableCommitsError`: When no commits can be squashed.
        subprocess.CalledProcessError: If the first ``git reset`` call
            unexpectedly fails
        `NoGithubPullRequestFoundError`: When using ``:github/pr`` as
            the range and no pull requests are found.
        `MultipleGithubPullRequestsFoundError`: When using ``:github/pr`` as
            the range and multiple pull requests are found.

    Returns:
        subprocess.CompletedProcess: The commit result. The commit result
        contains either a failed pre-commit hook result or a successful/failed
        commit result.
    """
    ref = github.get_pull_request_base() if ref == GITHUB_PR else ref
    range = f'{ref}..'

    commits = CommitRange(range=range)
    if not commits:
        raise exceptions.NoSquashableCommitsError('No commits to squash')

    # If there is a valid commit, use it as the default values for the
    # squashed commit message. Note that we look for the last valid commit
    valid_commits = commits.filter('is_valid', True)
    last_valid_commit = valid_commits[-1] if valid_commits else None

    defaults = last_valid_commit.schema_data if last_valid_commit else {}

    # Reset to the common ancestor of the ref point
    common_ancestor = utils.shell_stdout(f'git merge-base {ref} HEAD')
    utils.shell(f'git reset --soft {common_ancestor}')

    try:
        # Prompt for the new commit message. Reset back to the last point
        # if anything goes wrong
        commit_result = commit(
            allow_empty=allow_empty, no_verify=no_verify, defaults=defaults
        )
    except (Exception, KeyboardInterrupt):
        utils.shell('git reset ORIG_HEAD')
        raise

    if commit_result.returncode != 0:
        utils.shell('git reset ORIG_HEAD')

    return commit_result
