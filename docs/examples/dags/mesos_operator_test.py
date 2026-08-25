"""Minimal integration DAG for the provider MesosOperator."""
from datetime import datetime

from airflow import DAG
from avmesos_airflow_provider.operators.mesos import MesosOperator

with DAG("mesos_operator_test", schedule=None, start_date=datetime(2024, 1, 1), catchup=False,
         tags=["mesos", "provider", "integration"]) as dag:
    MesosOperator(
        task_id="run_on_mesos", image="alpine:3.20", command="echo mesos-operator-ok",
        cpus=0.1, mem_limit="128m", attributes=["airflow:true"],
        airflow_scheduler_url="{{ var.value.get('mesos_operator_api_url', 'http://localhost:11000') }}",
        startup_timeout=300,
    )