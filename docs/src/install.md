# How to install the AV Mesos Airflow Provider

To install the Mesos Airflow Provider, you have to to the following steps:

1. Install the provider

```bash
pip install avmesos_airflow_provider
```

2. Configure Airflow to use the new executor

```bash
vim airflow.cfg

[core]
executor = avmesos_airflow_provider.executors.mesos_executor.MesosExecutor

[mesos]
mesos_ssl = False
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
docker_environment = '{ "name":"<KEY>", "value":"<VALUE>" }, { ... },' // << do not forget the comma at the end.
api_username = user
api_password = password
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
                docker_url='unix:///var/run/docker.sock'
                executor_config={
                       "cpus": 2.0,
                       "mem_limit": 2048
                }         
        )

        t2
```
