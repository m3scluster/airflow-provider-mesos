# Provider for Apache Airflow 2.x to schedule Apache Mesos

This provider for Apache Airflow contain the following features:

- MesosExecuter - A scheduler to run Airflow DAG's on mesos
- MesosOperator - To executer Airflow tasks on mesos. (TODO)

## Requirements

- Airflow 2.x
- Apache Mesos minimum 1.6.x

## How to install and configure

On the Airflow Server, we have to install the mesos provider.

```bash
pip install avmesos_airflow_provider
```

Then we will configure Airflow.

```bash
vim airflow.cfg

executor = avmesos_airflow_provider.executors.mesos_executor.MesosExecutor

[mesos]
master = leader.mesos:5050
framework_name = Airflow
checkpoint = True
failover_timeout = 604800
command_shell = True
task_cpu = 1
task_memory = 20000
authenticate = True
default_principal = <MESOS USER>
default_secret = <MESOS PASSWORD>
docker_image_slave = <AIRFLOW DOCKER IMAGE>
docker_volume_driver = local
docker_volume_dag_name = airflowdags
docker_volume_dag_container_path = /home/airflow/airflow/dags/
docker_sock = /var/run/docker.sock
docker_volume_logs_name = airflowlogs
docker_volume_logs_container_path = /home/airflow/airflow/logs/
docker_environment = '[{ "name":"<KEY>", "value":"<VALUE>" }, { ... }]'
api_username = <USERNAME FOR THIS API>
api_password = <PASSWORD FOR THIS API>

```

## DAG example with mesos executor


```python
from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.dummy_operator import DummyOperator
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.operators.python import PythonOperator

default_args = {
        'owner'                 : 'airflow',
        'description'           : 'Use of the DockerOperator',
        'depend_on_past'        : True,
}

with DAG('docker_dag2', default_args=default_args, schedule_interval="*/10 * * * * ", catchup=True, start_date=datetime.now()) as dag:
        t2 = DockerOperator(
                task_id='docker_command',
                image='centos:latest',
                api_version='auto',
                auto_remove=False,
                command="/bin/sleep 600",
                docker_url='unix:///var/run/docker.sock',
                executor_config={
                        "MesosExecutor": {
                                "cpus": 2.0,
                                "mem_limit": 2048
                        }
                }         
        )

        t2
```
