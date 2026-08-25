# MesosOperator

`MesosOperator` runs one container task under Apache Mesos. Its behavior follows the Airflow `DockerOperator` model, but execution takes place through the MesosExecutor API.

## Example

```python
from datetime import datetime

from airflow import DAG
from avmesos_airflow_provider.operators.mesos import MesosOperator

with DAG(
    dag_id="mesos_operator_example",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    MesosOperator(
        task_id="hello_mesos",
        image="alpine:3.20",
        command="echo hello from Mesos",
        cpus=0.1,
        mem_limit="128m",
        attributes=["airflow:true"],
    )
```

## Parameters

| Parameter | Description |
|---|---|
| `image` | Container image; required. |
| `command` | String or argument list. Strings are executed through `/bin/sh -c`. |
| `cpus` | Requested CPU resources. |
| `mem_limit` | Requested memory, for example `128m` or a number. `memlimit` remains available as an alias. |
| `disk` | Requested Mesos disk resources. |
| `environment` | Dictionary of environment variables. |
| `attributes` | List of Mesos attribute constraints. |
| `force_pull` | Controls whether the image should be pulled again. |
| `network_mode` | Docker network mode. |
| `user` | User inside the container. |
| `volumes` | Volume specifications. |
| `airflow_scheduler_url` | Executor API URL; defaults to `operator_api_url` or `http://localhost:11000`. |
| `poll_interval` | Seconds between status requests. |
| `startup_timeout` | Maximum wait time in seconds. |

Airflow standard parameters such as `task_id`, `retries`, `pool`, and `queue` are supported through `BaseOperator`.

## Status behavior

The operator succeeds when the status is:

```text
TASK_FINISHED
```

The following states raise `AirflowException`:

```text
TASK_FAILED
TASK_ERROR
TASK_KILLED
TASK_LOST
TASK_UNREACHABLE
```

HTTP errors, invalid JSON responses, and exceeding `startup_timeout` are also reported as task failures.

## Cancellation limitation

The current executor API has no separate kill endpoint for directly queued operator tasks. `on_kill()` logs this limitation. For long-running tasks, use Airflow timeouts and container commands that can be stopped in a controlled way.
