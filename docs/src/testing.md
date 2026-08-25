# Entwicklung und Tests

## Nix-Umgebung

Die Datei `shell.nix` stellt Python, Airflow, PostgreSQL und die Provider-Abhängigkeiten bereit:

```bash
nix-shell
```

Der Shell-Hook erstellt eine virtuelle Umgebung unter `/tmp/python-dev`, richtet die lokale Airflow-Datenbank ein und installiert den Provider editable.

## Unit-Tests

Die Unit-Tests verwenden synthetische HTTP-Antworten und benötigen keinen Mesos- oder Airflow-Live-Dienst:

```bash
make test
```

Der Test-Target nutzt:

```bash
python3 -m unittest discover -s tests -v
```

## Build

```bash
make build
```

Damit werden Source-Distribution und Wheel erzeugt. Vor dem Commit sollten mindestens `make test`, `make build` und `git diff --check` ausgeführt werden.

## Live-Smoke-Test

Für eine echte Integration kann das Test-DAG in Airflow geladen und manuell gestartet werden. Voraussetzungen sind ein laufender Airflow-Scheduler mit `MesosExecutor`, eine erreichbare Executor-API auf Port 11000 und ein Mesos-Cluster mit passenden Agent-Attributen.

Die Mesos-Master-UI auf Port 5050 ist nur zur Beobachtung geeignet. Der Operator spricht nicht direkt mit der Master-UI.
