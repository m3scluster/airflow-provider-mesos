# DAG examples

## MesosExecutor

The executor distributes regular Airflow tasks through Mesos. The DAG task itself does not need a special operator class:

```python
from datetime import datetime
from airflow import DAG
from airflow.providers.standard.operators.bash import BashOperator

with DAG("executor_example", schedule=None, start_date=datetime(2024, 1, 1), catchup=False) as dag:
    BashOperator(
        task_id="show_date",
        bash_command="date",
        executor_config={
            "cpus": 0.2,
            "mem_limit": "256m",
            "attributes": ["airflow:true"],
        },
    )
```

## MesosOperator

For one container task:

```python
from datetime import datetime
from airflow import DAG
from avmesos_airflow_provider.operators.mesos import MesosOperator

with DAG("operator_example", schedule=None, start_date=datetime(2024, 1, 1), catchup=False) as dag:
    run = MesosOperator(
        task_id="run_command",
        image="alpine:3.20",
        command=["/bin/sh", "-c", "echo operator-ok && uname -a"],
        cpus=0.1,
        mem_limit="128m",
        environment={"EXAMPLE_MODE": "true"},
        attributes=["airflow:true"],
    )
```

A complete, intentionally short test DAG is available at `docs/examples/dags/mesos_operator_test.py`.
