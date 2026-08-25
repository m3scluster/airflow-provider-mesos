# Architecture

The provider offers two distinct execution paths:

## MesosExecutor

`MesosExecutor` replaces the Airflow executor. Airflow submits scheduled task workloads to a Mesos framework. The framework accepts Mesos offers and starts Airflow tasks as container tasks.

This path is suitable when an entire Airflow DAG, or many regular Airflow tasks, should be distributed through Mesos.

## MesosOperator

`MesosOperator` runs inside a regular Airflow DAG and starts exactly one task as a Mesos container. It is modeled after `DockerOperator`, but uses the local API provided by `MesosExecutor`.

The flow is:

1. The operator sends the container request to `POST /v0/queue_command`.
2. The MesosExecutor queues the request and accepts a matching Mesos offer.
3. The operator polls `GET /v0/task/<task_id>`.
4. The operator waits for `TASK_FINISHED` or reports a terminal failure to Airflow.

The API runs at `http://localhost:11000` by default. It is provided by the scheduler process and is not the Mesos master API on port 5050.

## Data flow

```text
Airflow Scheduler
      |
      | MesosExecutor API :11000
      v
MesosExecutor Framework
      |
      | Mesos scheduler protocol
      v
Mesos Master :5050
      |
      v
Mesos Agent -> Docker/Mesos Container
```

The operator does not create its own Mesos framework. Offer distribution, resource checking, and framework authentication therefore remain centralized in the existing executor.
