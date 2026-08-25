# Airflow Mesos Provider

The Airflow Mesos Provider integrates Apache Airflow with Apache Mesos.

It provides two execution models:

- **MesosExecutor:** distributes regular Airflow task workloads through a Mesos framework.
- **MesosOperator:** starts a single DAG task as a Mesos container and waits for it to finish.

## Quick start

1. Install the provider and configure Airflow: [Installation](install.md)
2. Understand the responsibilities and data flow: [Architecture](architecture.md)
3. Use the [MesosOperator](operator.md) for individual container tasks.
4. Read the [DAG examples](examples.md) for complete examples.
5. Verify the setup with [Testing and development](testing.md).

## Requirements

- Apache Airflow 3.x recommended; the provider declares Airflow `>=2.0`.
- Apache Mesos 1.6 or newer.
- Python 3.x.
- For Docker containers: a Mesos agent with the Docker containerizer enabled and access to the required image.

SSL and Mesos authentication are optional, but recommended for production clusters.

## Further documentation

- [Configuration](configuration.md)
- [Executor API](api.md)
- [Troubleshooting](troubleshooting.md)
