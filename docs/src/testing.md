# Development and testing

## Nix environment

`shell.nix` provides Python, Airflow, PostgreSQL, and the provider dependencies:

```bash
nix-shell
```

The shell hook creates a virtual environment under `/tmp/python-dev`, initializes the local Airflow database, and installs the provider in editable mode.

## Unit tests

The unit tests use synthetic HTTP responses and do not require a live Mesos or Airflow service:

```bash
make test
```

The test target runs:

```bash
python3 -m unittest discover -s tests -v
```

## Build

```bash
make build
```

This creates a source distribution and wheel. Before committing, run at least `make test`, `make build`, and `git diff --check`.

## Live smoke test

For a real integration test, load the test DAG into Airflow and trigger it manually. Requirements are a running Airflow scheduler with `MesosExecutor`, a reachable executor API on port 11000, and a Mesos cluster with matching agent attributes.

The Mesos master UI on port 5050 is for observation only. The operator does not communicate directly with the master UI.
