# Airflow Mesos Provider

Der Airflow Mesos Provider integriert Apache Airflow mit Apache Mesos.

Er bietet zwei Ausführungsmodelle:

- **MesosExecutor:** verteilt normale Airflow-Task-Workloads über ein Mesos-Framework.
- **MesosOperator:** startet einen einzelnen DAG-Task als Mesos-Container und wartet auf dessen Abschluss.

## Schnellstart

1. Provider installieren und Airflow konfigurieren: [Installation](install.md)
2. Architektur und Zuständigkeiten verstehen: [Architektur](architecture.md)
3. Für einzelne Container-Tasks den [MesosOperator](operator.md) verwenden.
4. Für vollständige Beispiele [DAG-Beispiele](examples.md) lesen.
5. Mit [Tests und Entwicklung](testing.md) verifizieren.

## Voraussetzungen

- Apache Airflow 3.x empfohlen; der Provider deklariert Airflow `>=2.0`.
- Apache Mesos 1.6 oder neuer.
- Python 3.x.
- Für Docker-Container: ein Mesos-Agent mit aktivem Docker-Containerizer und Zugriff auf das gewünschte Image.

SSL und Mesos-Authentifizierung sind optional, werden für produktive Cluster aber empfohlen.

## Weitere Dokumentation

- [Konfiguration](configuration.md)
- [Executor-API](api.md)
- [Fehlerbehebung](troubleshooting.md)