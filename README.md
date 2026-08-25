# Provider for Apache Airflow schedule Apache Mesos

[![Docs](https://img.shields.io/static/v1?label=&message=Issues&color=brightgreen)](https://github.com/m3scluster/airflow-provider-mesos/issues)
[![Chat](https://img.shields.io/static/v1?label=&message=Chat&color=brightgreen)](https://matrix.to/#/#mesos:matrix.aventer.biz?via=matrix.aventer.biz)
[![Docs](https://img.shields.io/static/v1?label=&message=Docs&color=brightgreen)](https://m3scluster.github.io/airflow-provider-mesos/)

This provider for Apache Airflow contain the following features:

- MesosExecuter - A scheduler to run Airflow DAG's on mesos
- MesosOperator - To execute individual Airflow tasks on Mesos.


## Issues

To open an issue, please use this place: https://github.com/m3scluster/airflow-provider-mesos/issues

## Requirements

- Airflow 3.x
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
mesos_ssl = True
master = leader.mesos:5050
framework_name = Airflow
checkpoint = True
mesos_attributes = ["airflow:true", "gpu:true?:cpu:true"]
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
docker_volume_dag_container_path = /airflow/airflow/dags/
docker_sock = /var/run/docker.sock
docker_volume_logs_name = airflowlogs
docker_volume_logs_container_path = /airflow/airflow/
docker_user_group_id = 998
docker_environment = [{ "name":"<KEY>", "value":"<VALUE>" }, { ... }]
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
                                "cpus": 2.0,
                                "mem_limit": 2048,
                                "attributes": ["gpu:true"]
                }         
        )

        t2
```

## Using MesosOperator

`MesosOperator` is modelled after `DockerOperator`, but submits one container
task to the Mesos executor framework API and waits for its terminal Mesos
status. The executor API listens on port `11000` by default; override it with
`mesos.operator_api_url` or the operator's `airflow_scheduler_url`.

```python
from datetime import datetime
from airflow import DAG
from avmesos_airflow_provider.operators.mesos import MesosOperator

with DAG("mesos_operator", schedule=None, start_date=datetime(2024, 1, 1), catchup=False) as dag:
    MesosOperator(
        task_id="hello",
        image="alpine:3.20",
        command="echo hello from Mesos",
        cpus=0.1,
        mem_limit="128m",
        attributes=["airflow:true"],
    )
```

## Using Mesos attributes

Within the airflow.cfg file, you can define default Mesos attributes that are
applied to every task.

As example:

```bash
mesos_attributes = ["airflow:true", "gpu:true?:cpu:true"]
```

When you add task-specific attributes within your DAG,...

```bash
executor_config={
  "cpus": 2.0,
  "mem_limit": 2048,
  "attributes": ["gpu:true"]
}
```

... they are combined with these default attributes. This allows you to both
supplement and override the default settings.

Specifically, what is the reasoning behind the convention used in the
`gpu:true?:cpu:true` attribute string?

The intention is that if a Mesos offer does include gpu=true, the task will
automatically default to using a CPU-only server, preventing the Data Science
team from needing to manually add attributes to each task. If a Data Science team
need GPU, they only has to add that specific attribute.

This is simply an illustrative example, and the GPU and CPU attributes can be
any valid string value.

## Development

For development and testing we deliver a nix-shell file to install airflow, our airflow provider and postgresql. 
To use it, please follow the following steps:

1. Run mesos-mini:

```bash
docker run --rm --name mesos --privileged=true --shm-size=30gb -it --net host avhost/mesos-mini:1.11.0-0.2.0-1 /lib/systemd/systemd
```

2. Use nix-shell:


```bash
nix-shell

> airflow scheduler
```

3. On the mesos-ui (http://localhost:5050) you will see Airflow as framework. 



