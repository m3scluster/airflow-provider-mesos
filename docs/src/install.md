# Installation

## Paketinstallation

```bash
pip install avmesos_airflow_provider
```

Der Provider benötigt außerdem eine kompatible Airflow-, `avmesos`- und HTTP-Umgebung. Für lokale Entwicklung stellt `shell.nix` eine reproduzierbare Umgebung bereit.

## Airflow konfigurieren

Für die Ausführung normaler Airflow-Tasks über Mesos:

```ini
[core]
executor = avmesos_airflow_provider.executors.mesos_executor.MesosExecutor
```

Die vollständige Beispielkonfiguration steht in [Konfiguration](configuration.md).

## Lokale Entwicklung

```bash
nix-shell
```

Die Nix-Shell installiert Airflow, `avmesos`, den Provider und PostgreSQL. Sie richtet außerdem die lokale Airflow-Datenbank und die DAG-Umgebung ein.

## MesosOperator verwenden

Der Operator benötigt keinen zweiten Executor. Der Airflow-Scheduler mit `MesosExecutor` stellt die interne API auf Port `11000` bereit. Ein Minimalbeispiel:

```python
from datetime import datetime

from airflow import DAG
from avmesos_airflow_provider.operators.mesos import MesosOperator

with DAG("hello_mesos", schedule=None, start_date=datetime(2024, 1, 1), catchup=False) as dag:
    MesosOperator(
        task_id="hello",
        image="alpine:3.20",
        command="echo hello",
        cpus=0.1,
        mem_limit="128m",
    )
```

Details befinden sich in der [Operator-Referenz](operator.md).