# Executor API

The API is provided by `MesosExecutor` in the Airflow scheduler. The default address is `http://localhost:11000`.

## POST `/v0/queue_command`

Queues a direct container task.

Example request body:

```json
{
  "airflow_task_id": "airflow.example.hello",
  "container_type": "DOCKER",
  "command": ["/bin/sh", "-c", "echo hello"],
  "image": "alpine:3.20",
  "cpus": 0.1,
  "mem_limit": "128m",
  "attributes": ["airflow:true"],
  "environment": {"MODE": "test"}
}
```

A successful acceptance returns HTTP 200. This only means that the request was accepted into the executor queue; Mesos execution has not necessarily finished yet.

## GET `/v0/task/<task_id>`

Returns the latest known Mesos status for the task. The `task_id` must be URL-encoded if it contains characters outside the usual task ID format.

The operator expects an object with a status field, for example:

```json
{
  "status": {
    "task_id": {"value": "airflow.example.hello"},
    "state": "TASK_FINISHED"
  }
}
```

During execution, `TASK_STAGING`, `TASK_STARTING`, and `TASK_RUNNING` may occur. Terminal failure states are translated into an Airflow task failure by the operator.

## Security

The API should only be reachable on the internal Airflow/scheduler network. Store credentials in Airflow configuration or secret backends, not in versioned DAGs. Mesos authentication to the cluster is configured separately through `[mesos]`.
