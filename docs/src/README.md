# Airflow Mesos Provider

## Introduction

There are two parts of the "Airflow Mesos Provider".

- Mesos Scheduler: These provide the possibility to schedule Airflow tasks over the Mesos infrastructure
- Mesos Operator: These will run the specific DAG Task direct as Mesos task.


## Requirements


- Apache Mesos min 1.6.0
- Mesos with SSL and Authentication is optional
- Airflow 2.x
- Python 3.x
