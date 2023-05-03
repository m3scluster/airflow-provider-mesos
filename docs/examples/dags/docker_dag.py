#!/usr/bin/env python
# -*- coding: utf-8 -*-

from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.dummy_operator import DummyOperator
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.operators.python import PythonOperator

default_args = {
        'owner'                 : 'airflow',
        'description'           : 'Use of the DockerOperator',
        'depend_on_past'        : True,
}

with DAG('docker_operator', default_args=default_args, schedule_interval="*/10 * * * * ", catchup=True, start_date=datetime.now()) as dag:
        t1 = DockerOperator(
                task_id='docker_command1',
                image='avhost/docker-airflow',
                api_version='auto',
                auto_remove=False,
                command="/bin/sleep 600",
                docker_url='unix:///var/run/docker.sock',
                executor_config={
                   "cpus": 2,
                   "mem_limit": 2048
                },
                cpus=8,
                mem_limit='64g'
        )

        t2 = DockerOperator(
                task_id='docker_command2',
                image='avhost/docker-airflow',
                api_version='auto',
                auto_remove=False,
                command="/bin/sleep 600",
                docker_url='unix:///var/run/docker.sock',
                executor_config={
                   "cpus": 2.0,
                   "mem_limit": 2048
                }         
        )

        t1
        t2