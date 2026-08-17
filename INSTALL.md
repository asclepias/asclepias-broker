# Local development

## General setup

Start the Docker services and wait for them to be ready:

```bash
docker compose up -d search db cache mq && docker/wait-for-services.sh
```

Make sure that the Python version matches with the one defined in the `Dockerfile` and the `Pipfile`:

```bash
python --version
```

If not, switch to the proper Python version, for instance with pyenv:

```bash
pyenv shell 3.xx
```

Create a virtual environment and activate it:

```bash
python -m venv .venv && source .venv/bin/activate
```

Install pipenv:

```bash
pip install pipenv
```

## Running the tests

Install the dependencies and the development dependencies:

```bash
pipenv install --dev
```

Run the tests:

```bash
./run-tests.sh
```

## Running the application

Install the dependencies:

```bash
pipenv install
```

Install the application:

```bash
pipenv run pip install -e .
```

Setup services initial structure:

```bash
pipenv run invenio alembic upgrade
pipenv run invenio db init create --verbose
pipenv run invenio index init --force
```

Run the web application:

```bash
pipenv run invenio run --cert docker/nginx/test.crt --key docker/nginx/test.key
```

The API should be functional, for instance:
<https://localhost:5000/api/relationships?id=10.21105/joss.00024&scheme=doi&relation=isCitedBy>

Run the scheduler:

```bash
pipenv run celery -A invenio_app.celery worker --beat --loglevel=INFO
```

## General teardown

Stop the Docker services

```bash
docker compose down
```
