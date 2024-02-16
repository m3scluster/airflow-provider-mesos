#!/usr/bin/env python
# -*- coding: utf-8 -*-

from airflow.models.dag import DAG
from datetime import datetime, timedelta
from airflow.providers.docker.operators.docker import DockerOperator

default_args = {
        'owner'                 : 'airflow',
        'description'           : 'Use of the DockerOperator',
        'depend_on_past'        : True,
        'retries'               : 1,
        'retry_delay'           : timedelta(minutes=5),        
}

with DAG('docker_operator', default_args=default_args, schedule=None, start_date=datetime.now(), tags=["example"]) as dag:
        t1 = DockerOperator(
                task_id='docker_command1',
                image='alpine:latest',
                api_version='auto',
                command="/bin/sleep 600",
                docker_url='unix:///var/run/docker.sock',
                retries=0,
                executor_config={
                   "cpus": 1,
                   "mem_limit": "2g"
                },
                cpus=1,
                mem_limit='64g'
        )

        t2 = DockerOperator(
                task_id='docker_command2',
                image='alpine:latest',
                api_version='auto',
                command="/bin/sleep 600",
                docker_url='unix:///var/run/docker.sock',
                retries=0,
                executor_config={
                   "cpus": 1,
                   "mem_limit": "2g"
                }         
        )

        t1 >> t2