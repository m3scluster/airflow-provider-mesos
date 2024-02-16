#!/usr/bin/env python
# -*- coding: utf-8 -*-

from airflow.models.dag import DAG
from datetime import datetime, timedelta
from airflow.operators.python import PythonOperator

default_args = {
        'owner'                 : 'airflow',
        'description'           : 'Use of the DockerOperator',
        'depend_on_past'        : True,
        'retries'               : 1,
        'retry_delay'           : timedelta(minutes=5),
}

with DAG('python_operator', default_args=default_args, schedule=None, start_date=datetime.now(), tags=["example"]) as dag:

        def my_function(x):
                i = 0
                while i <= 1000000000:
                        print("This is a Python function.")
                        i = i+1


        t1 = PythonOperator(
                task_id='python_command1',
                python_callable=my_function,
                retries=0,                
                dag=dag
        )

        t1

