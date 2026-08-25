# Configuration

## Airflow executor

Enable the executor in `airflow.cfg`:

```ini
[core]
executor = avmesos_airflow_provider.executors.mesos_executor.MesosExecutor
```

## Mesos configuration

The values below are examples. Adapt hosts, credentials, and images to your environment.

```ini
[mesos]
mesos_ssl = True
master = mesos-master.example.invalid:5050
framework_name = Airflow
checkpoint = True
failover_timeout = 604800
command_shell = True

task_cpu = 0.1
task_memory = 512
task_disk = 1000

authenticate = True
default_principal = <MESOS_PRINCIPAL>
default_secret = <MESOS_SECRET>

docker_image_slave = <AIRFLOW_RUNTIME_IMAGE>
docker_volume_driver = local
docker_volume_dag_name = airflowdags
docker_volume_dag_container_path = /airflow/dags/
docker_volume_logs_name = airflowlogs
docker_volume_logs_container_path = /airflow/logs/
docker_sock = /var/run/docker.sock
docker_user_group_id = <DOCKER_GROUP_ID>
docker_network_mode = bridge
docker_environment = []

api_username = <API_USERNAME>
api_password = <API_PASSWORD>
operator_api_url = http://localhost:11000
```

`operator_api_url` is the address used by `MesosOperator` when no `airflow_scheduler_url` is set on the task.

## Attributes

Global attributes apply to executor tasks. Task-specific attributes are added by the operator or through `executor_config`:

```ini
mesos_attributes = ["airflow:true", "gpu:true?:cpu:true"]
```

An operator can specify additional attributes:

```python
MesosOperator(
    task_id="cpu_task",
    image="alpine:3.20",
    command="echo hello",
    attributes=["cpu:true"],
)
```

Do not commit secrets or production infrastructure addresses in DAG files. Use Airflow Connections, Variables, or external secret backends for environment-specific values.
