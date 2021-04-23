from airflow import DAG
from airflow.decorators import task, dag
from airflow.operators.python_operator import PythonOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.operators.postgres_operator import PostgresOperator
from datetime import datetime
from airflow.models.baseoperator import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.operators.python import task, get_current_context
import pandas as pd
import json

# See https://marclamberti.com/blog/airflow-xcom/
default_args={
    "owner": "airflow",
	"start_date": datetime.today()
}

dag = DAG(
    "my_dag_complex",
    default_args=default_args,
    schedule_interval="*/120 * * * *"
)


def extract_fun(ti):
    people = {
        'Firstnames': ['James','Corolla','Mark','Eddy'],
        'Lastnames': ['Wick','Leto','Smith','Etwan']
    }
    ti.xcom_push(key='my_people', value=people)
    return people
    

def process_fun(ti):
    value = "demo!"
    print(f"Processing: {value}")

    fetched_value = ti.xcom_pull(key='my_people', task_ids=['extract'])
    print(f"Retrieved value (XCOM): {fetched_value}")
    
    some_values = fetched_value[0]['Firstnames']
    print(f"Retrieved value (XCOM): {some_values}")


extract = PythonOperator(
    task_id="extract",
    python_callable=extract_fun,
    dag=dag
)

process = PythonOperator(
    task_id="process",
    python_callable=process_fun,
    dag=dag
)

invokeTransformOperator = SimpleHttpOperator(
    task_id='invoke_transform_operation',
    #http_conn_id='urbinite_http',
    method='POST',
    endpoint='post',
    data=json.dumps({ "uuid": '{{run_id}}' , "Firstnames": '{{ ti.xcom_pull(task_ids=[\'extract\'])[0][\'Firstnames\'] }}' }),
    headers={"Content-Type": "application/json"},
    response_check=lambda response: response.json()['result'] == 'OK',
    dag=dag
)

extract >> process >> invokeTransformOperator