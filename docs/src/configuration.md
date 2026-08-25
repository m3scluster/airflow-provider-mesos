# Konfiguration

## Airflow-Executor

In `airflow.cfg` wird der Executor aktiviert:

```ini
[core]
executor = avmesos_airflow_provider.executors.mesos_executor.MesosExecutor
```

## Mesos-Konfiguration

Die Werte sind Beispiele. Hosts, Zugangsdaten und Images müssen an die eigene Umgebung angepasst werden.

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

`operator_api_url` ist die Adresse, die der `MesosOperator` verwendet, wenn kein `airflow_scheduler_url` am Task gesetzt ist.

## Attribute

Globale Attribute gelten für Executor-Tasks. Task-spezifische Attribute werden vom Operator beziehungsweise `executor_config` ergänzt:

```ini
mesos_attributes = ["airflow:true", "gpu:true?:cpu:true"]
```

Ein Operator kann zusätzlich Folgendes angeben:

```python
MesosOperator(
    task_id="cpu_task",
    image="alpine:3.20",
    command="echo hello",
    attributes=["cpu:true"],
)
```

Keine Secrets oder produktiven Infrastrukturadressen in DAG-Dateien versionieren. Für Umgebungen sollten Airflow Connections, Variables oder externe Secret-Backends verwendet werden.
