# How to install the AV Mesos Airflow Provider

To install the Mesos Airflow Provider, you have to to the following steps:

1. Install the provider

```bash
pip install avmesos_airflow_provider
```

2. Configure Airflow to use the new executor

```bash
vim airflow.cfg

[core]
executor = avmesos_airflow_provider.executors.mesos_executor.MesosExecutor

```
