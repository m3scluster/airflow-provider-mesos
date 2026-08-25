from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import boto3

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 3, 21),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

aws_credentials_id = 'my_aws_credentials'

s3_bucket = 'meine-s3-bucket'
source_key = 'path/to/source/file.txt'
target_key = 'path/to/target/file.txt'

def copy_file_to_s3(**kwargs):
    s3 = boto3.client('s3', aws_access_key_id=aws_credentials_id['aws_access_key'],
                      aws_secret_access_key=aws_credentials_id['aws_secret_key'])
    s3.copy_object(Bucket=s3_bucket, CopySource={'Bucket': s3_bucket, 'Key': source_key},
                   Key=target_key)

dag = DAG(
    'copy_file_from_s3',
    default_args=default_args,
    schedule=timedelta(days=1),
    description='Kopiert eine Datei von S3 nach einem anderen Speicherort'
)

start_operator = PythonOperator(
    task_id='start',
    python_callable=lambda: None,
    dag=dag
)

copy_task = PythonOperator(
    task_id='copy_file_to_s3',
    python_callable=copy_file_to_s3,
    dag=dag
)

end_operator = PythonOperator(
    task_id='end',
    python_callable=lambda: None,
    dag=dag
)

start_operator >> copy_task >> end_operator

