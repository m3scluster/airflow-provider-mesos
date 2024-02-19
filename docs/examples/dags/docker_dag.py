#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import os

from airflow.models.dag import DAG
from datetime import datetime, timedelta
from airflow.operators.bash import BashOperator
from airflow.providers.docker.operators.docker import DockerOperator

ENV_ID = os.environ.get("SYSTEM_TESTS_ENV_ID")

default_args = {
        'owner'                 : 'airflow',
        'description'           : 'Use of the DockerOperator',
        'depend_on_past'        : True,
        'retries'               : 1,
        'retry_delay'           : timedelta(minutes=5),        
}

with DAG('docker_operator', default_args=default_args, schedule=None, start_date=datetime.now(), tags=["example"]) as dag:
        t1 = DockerOperator(
            docker_url="unix://var/run/docker.sock",  # Set your docker URL
            command="/bin/sleep 30",
            image="centos:latest",
            network_mode="bridge",
            task_id="docker_op_tester",
            executor_config={
                "cpus": 1.0,
                "mem_limit": "200m"
            },
            dag=dag,
        )
        t1

