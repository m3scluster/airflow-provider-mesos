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

with DAG('python_operator', default_args=default_args, schedule_interval="*/10 * * * * ", catchup=True, start_date=datetime.now()) as dag:

        def my_function(x):
                print("This is a Python function.")


        t1 = PythonOperator(
                task_id='python_command1',
                provide_context=True,
                python_callable=my_function,
                retries=2,                
                op_kwargs={'source': 'test', 'target': 'done/test'},
                dag=dag
        )

        t1

