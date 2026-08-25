# Fehlerbehebung

## Operator bleibt im Polling

Prüfen:

1. Läuft der Airflow-Scheduler mit `MesosExecutor`?
2. Ist `airflow_scheduler_url` korrekt und auf Port 11000 erreichbar?
3. Ist das Framework im Mesos-Master registriert?
4. Gibt es passende CPU-, Speicher- und Attribut-Offers?

Die Executor-API meldet `HTTP 200` beim Queueing nur für die Annahme in die Warteschlange. Der Operator wartet danach weiter auf den Mesos-Status.

## `TASK_FAILED` oder `TASK_ERROR`

Mesos-Agent-Logs und die Task-Details in der Mesos-UI prüfen. Häufige Ursachen sind ein nicht verfügbares Image, fehlende Ressourcen, nicht passende Attribute oder ein falscher Container-/Netzwerkmodus.

## `TASK_LOST`

Der Agent oder die Framework-Verbindung ist verloren gegangen. Prüfen, ob das Framework neu verbunden ist und ob der Agent aktiv ist.

## API antwortet mit 401

Die API-Konfiguration und der verwendete Endpunkt prüfen. `/v0/dags` ist geschützt; der Operator verwendet `/v0/queue_command` und `/v0/task/<task_id>`. Die API sollte nicht über einen öffentlichen Reverse Proxy ohne passende Authentifizierung veröffentlicht werden.

## DAG wird nicht geladen

Zuerst den Import isoliert prüfen:

```bash
airflow dags list-import-errors
```

Danach sicherstellen, dass `dags_folder` auf das Verzeichnis mit der DAG-Datei zeigt und dass der Provider in derselben Python-Umgebung installiert ist wie Airflow.

## Ressourcen passen nicht

`cpus`, `mem_limit` und `disk` müssen zu den freien Mesos-Offers passen. Bei Attributen muss mindestens ein aktiver Agent alle Bedingungen erfüllen. Globale Attribute aus `mesos_attributes` und task-spezifische Attribute werden zusammen verwendet.
