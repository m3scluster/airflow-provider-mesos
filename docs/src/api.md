# Executor-API

Die API wird vom `MesosExecutor` im Airflow-Scheduler bereitgestellt. Standardadresse ist `http://localhost:11000`.

## POST `/v0/queue_command`

Reiht einen direkten Container-Task ein.

Beispielkörper:

```json
{
  "airflow_task_id": "airflow.example.hello",
  "container_type": "DOCKER",
  "command": ["/bin/sh", "-c", "echo hello"],
  "image": "alpine:3.20",
  "cpus": 0.1,
  "mem_limit": "128m",
  "attributes": ["airflow:true"],
  "environment": {"MODE": "test"}
}
```

Eine erfolgreiche Annahme liefert HTTP 200. Das bedeutet nur, dass der Auftrag in die Executor-Warteschlange übernommen wurde; die Mesos-Ausführung ist zu diesem Zeitpunkt noch nicht abgeschlossen.

## GET `/v0/task/<task_id>`

Liefert den zuletzt bekannten Mesos-Status des Tasks. Der `task_id` muss URL-sicher kodiert werden, wenn er Zeichen außerhalb des üblichen Task-ID-Formats enthält.

Der Operator erwartet ein Objekt mit einem Statusfeld, zum Beispiel:

```json
{
  "status": {
    "task_id": {"value": "airflow.example.hello"},
    "state": "TASK_FINISHED"
  }
}
```

Während der Ausführung können `TASK_STAGING`, `TASK_STARTING` und `TASK_RUNNING` auftreten. Terminale Fehlerzustände werden vom Operator in einen Airflow-Task-Fehler übersetzt.

## Sicherheit

Die API sollte nur auf dem internen Airflow-/Scheduler-Netzwerk erreichbar sein. Zugangsdaten gehören in Airflow-Konfiguration oder Secret-Backends und nicht in versionierte DAGs. Die Mesos-Authentifizierung gegenüber dem Cluster wird separat über die `[mesos]`-Konfiguration gesteuert.
