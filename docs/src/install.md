# Installation

## Package installation

```bash
pip install avmesos_airflow_provider
```

The provider also requires a compatible Airflow, `avmesos`, and HTTP environment. For local development, `shell.nix` provides a reproducible environment.

## Configure Airflow

To run regular Airflow tasks through Mesos:

```ini
[core]
executor = avmesos_airflow_provider.executors.mesos_executor.MesosExecutor
```

The complete example configuration is available in [Configuration](configuration.md).

## Local development

```bash
nix-shell
```

The Nix shell installs Airflow, `avmesos`, the provider, and PostgreSQL. It also initializes the local Airflow database and DAG environment.

## Use MesosOperator

The operator does not require a second executor. The Airflow scheduler with `MesosExecutor` exposes the internal API on port `11000`. A minimal example:

```python
from datetime import datetime

from airflow import DAG
from avmesos_airflow_provider.operators.mesos import MesosOperator

with DAG("hello_mesos", schedule=None, start_date=datetime(2024, 1, 1), catchup=False) as dag:
    MesosOperator(
        task_id="hello",
        image="alpine:3.20",
        command="echo hello",
        cpus=0.1,
        mem_limit="128m",
    )
```

See the [Operator reference](operator.md) for details.
