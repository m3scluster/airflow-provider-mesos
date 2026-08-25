# MesosOperator

`MesosOperator` führt einen einzelnen Container-Task unter Apache Mesos aus. Das Verhalten orientiert sich am Airflow `DockerOperator`, die Ausführung erfolgt jedoch über die MesosExecutor-API.

## Beispiel

```python
from datetime import datetime

from airflow import DAG
from avmesos_airflow_provider.operators.mesos import MesosOperator

with DAG(
    dag_id="mesos_operator_example",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
) as dag:
    MesosOperator(
        task_id="hello_mesos",
        image="alpine:3.20",
        command="echo hello from Mesos",
        cpus=0.1,
        mem_limit="128m",
        attributes=["airflow:true"],
    )
```

## Parameter

| Parameter | Beschreibung |
|---|---|
| `image` | Container-Image; erforderlich. |
| `command` | String oder Argumentliste. Strings laufen über `/bin/sh -c`. |
| `cpus` | Angeforderte CPU-Ressourcen. |
| `mem_limit` | Angeforderter Speicher, zum Beispiel `128m` oder eine Zahl. `memlimit` bleibt als Alias verfügbar. |
| `disk` | Angeforderter Mesos-Datenträger. |
| `environment` | Dictionary mit Umgebungsvariablen. |
| `attributes` | Liste von Mesos-Attributbedingungen. |
| `force_pull` | Steuert, ob das Image erneut gezogen werden soll. |
| `network_mode` | Docker-Netzwerkmodus. |
| `user` | Benutzer im Container. |
| `volumes` | Volume-Angaben. |
| `airflow_scheduler_url` | URL der Executor-API; Standard ist `operator_api_url` beziehungsweise `http://localhost:11000`. |
| `poll_interval` | Sekunden zwischen Statusabfragen. |
| `startup_timeout` | Maximale Wartezeit in Sekunden. |

Airflow-Standardparameter wie `task_id`, `retries`, `pool` und `queue` werden über `BaseOperator` unterstützt.

## Statusverhalten

Der Operator beendet sich erfolgreich bei:

```text
TASK_FINISHED
```

Folgende Zustände führen zu `AirflowException`:

```text
TASK_FAILED
TASK_ERROR
TASK_KILLED
TASK_LOST
TASK_UNREACHABLE
```

HTTP-Fehler, ungültige JSON-Antworten und das Überschreiten von `startup_timeout` werden ebenfalls als Task-Fehler gemeldet.

## Einschränkung bei Abbruch

Die aktuelle Executor-API besitzt keinen separaten Kill-Endpunkt für direkt eingereihte Operator-Tasks. `on_kill()` protokolliert diese Einschränkung. Für lange Tasks sollten Airflow-Timeouts und kurze, kontrolliert abbrechbare Container-Kommandos verwendet werden.
