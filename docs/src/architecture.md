# Architektur

Der Provider stellt zwei unterschiedliche Ausführungswege bereit:

## MesosExecutor

`MesosExecutor` ersetzt den Airflow-Executor. Airflow übergibt eingeplante Task-Workloads an ein Mesos-Framework. Das Framework nimmt Mesos-Offers an und startet daraus Airflow-Tasks als Container-Tasks.

Dieser Weg eignet sich, wenn ein gesamter Airflow-DAG oder viele normale Airflow-Tasks über Mesos verteilt werden sollen.

## MesosOperator

`MesosOperator` läuft innerhalb eines normalen Airflow-DAGs und startet genau einen einzelnen Task als Mesos-Container. Er ist dem `DockerOperator` nachempfunden, verwendet aber die vom `MesosExecutor` bereitgestellte lokale API.

Der Ablauf ist:

1. Der Operator sendet den Container-Auftrag an `POST /v0/queue_command`.
2. Der MesosExecutor reiht den Auftrag ein und nimmt ein passendes Mesos-Offer an.
3. Der Operator fragt `GET /v0/task/<task_id>` ab.
4. Der Operator wartet auf `TASK_FINISHED` oder meldet einen terminalen Fehler an Airflow.

Die API läuft standardmäßig auf `http://localhost:11000`. Sie wird vom Scheduler-Prozess bereitgestellt und ist nicht die Mesos-Master-API auf Port 5050.

## Datenfluss

```text
Airflow Scheduler
      |
      | MesosExecutor API :11000
      v
MesosExecutor Framework
      |
      | Mesos scheduler protocol
      v
Mesos Master :5050
      |
      v
Mesos Agent -> Docker/Mesos Container
```

Der Operator erzeugt kein eigenes Mesos-Framework. Dadurch bleiben Offer-Verteilung, Ressourcenprüfung und Framework-Authentifizierung zentral im bestehenden Executor.
