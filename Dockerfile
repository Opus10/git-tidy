FROM opus10/circleci-public-python-library
USER root

RUN mkdir /code
WORKDIR /code

# Install requirements
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

# Install root project
COPY . .
RUN poetry install

# Configure the git commit template message
RUN poetry run git-tidy --template -o .gitcommit.tpl
RUN poetry run git config --local commit.template .gitcommit.tpl
