# Troubleshooting

## Operator remains in polling

Check the following:

1. Is the Airflow scheduler running with `MesosExecutor`?
2. Is `airflow_scheduler_url` correct and reachable on port 11000?
3. Is the framework registered with the Mesos master?
4. Are there matching CPU, memory, and attribute offers?

The executor API returns `HTTP 200` during queueing only to confirm acceptance into the queue. The operator then continues waiting for the Mesos status.

## `TASK_FAILED` or `TASK_ERROR`

Check Mesos agent logs and the task details in the Mesos UI. Common causes include an unavailable image, insufficient resources, unmatched attributes, or an incorrect container/network mode.

## `TASK_LOST`

The agent or framework connection was lost. Check whether the framework has reconnected and whether the agent is active.

## API returns 401

Check the API configuration and the endpoint being used. `/v0/dags` is protected; the operator uses `/v0/queue_command` and `/v0/task/<task_id>`. Do not expose the API through a public reverse proxy without suitable authentication.

## DAG is not loaded

First check imports in isolation:

```bash
airflow dags list-import-errors
```

Then make sure `dags_folder` points to the directory containing the DAG and that the provider is installed in the same Python environment as Airflow.

## Resources do not match

`cpus`, `mem_limit`, and `disk` must fit the available Mesos offers. For attributes, at least one active agent must satisfy every constraint. Global attributes from `mesos_attributes` and task-specific attributes are used together.
