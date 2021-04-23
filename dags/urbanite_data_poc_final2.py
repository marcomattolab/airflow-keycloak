import requests
import uuid
import json
from decimal import Decimal
import pandas as pd
import psycopg2 as pg
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from airflow.models import Variable
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.operators.postgres_operator import PostgresOperator
from airflow.sensors.sql_sensor import SqlSensor
from airflow.models.baseoperator import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.operators.python import task, get_current_context

#TODO Define Variables and Connections
#ETL_SRC_NAME = Variable.get ("ETL_SRC_NAME_ES")
#ETL_SRC_URL = Variable.get ("ETL_SRC_URL_ES")
#ETL_DST_URL = Variable.get ("ETL_DST_URL_ES")

ETL_SRC_NAME = "api.citybik.es"
ETL_SRC_URL = "https://api.citybik.es/v2/networks/bilbon-bizi"
ETL_DST_URL = "http://172.23.0.1:5000/execution/"

default_args={
    "owner": "airflow",
    #"start_date": datetime.today() - timedelta(days=1)
	"start_date": datetime.today()
}

dag = DAG(
    "urbanite_data_poc_final2",
    default_args=default_args
    #,schedule_interval="*/60 * * * *"
)

#############################################################################
# GET / Extract and fetch Data To Local
#############################################################################
def fetchDataToLocal():
    context = get_current_context()
    uuidTime = context['ts']
    print("URBANITE:= fetchDataToLocal uuidTime: '{}' in progress...".format(uuidTime))

    # fetching the request
    response = requests.get(ETL_SRC_URL)

    # convert the response to a pandas dataframe, then save as file to the data folder in our project directory
    df = pd.DataFrame(json.loads(response.content))

    # for integrity reasons, let's attach the current date to the filename
    df.to_json("/opt/airflow/logs/urbanite_poc_{}.json".format(datetime.today().strftime("%Y%m%d")))
    print("URBANITE:= fetchDataToLocal uuidTime: '{}' has been successfully completed and file generated!!".format(uuidTime))


#############################################################################
# Get Result: Get Categorized Result And Save File json on filesystem
#############################################################################
def getResultAndSave():
    context = get_current_context()
    uuidTime = context['run_id']
    print("URBANITE:= getResultAndSave uuidTime: '{}' in progress .....".format(uuidTime))

    # fetching the request
    response = requests.get(ETL_DST_URL+uuidTime)

    # save data into file system as JSON file
    data = json.loads(response.content)
    with open("/opt/airflow/logs/urbanite_poc_generated_{}.json".format(datetime.today().strftime("%Y%m%d")), 'w') as outfile:
        json.dump(data, outfile)

    print("URBANITE:= getResultAndSave uuidTime: '{}' has been successfully completed and file generated !!!!".format(uuidTime))


fetchDataToLocal = PythonOperator(
    task_id="fetch_data_to_local",
    python_callable=fetchDataToLocal,
    dag=dag
)

invokeTransformOperator = SimpleHttpOperator(
    task_id='invoke_transform_operation',
    http_conn_id='urbinite_http',
    method='POST',
    endpoint='post-job',
    data=json.dumps({"uuid": '{{run_id}}'}),
    headers={"Content-Type": "application/json"},
    response_check=lambda response: response.json()['result'] == 'OK',
    dag=dag
)

sensorTransformCompleted = HttpSensor(
    task_id='sensor_operation_completed',
    http_conn_id='urbinite_http',
    endpoint='get-status',
    request_params={"uuid": '{{run_id}}'},
    response_check=lambda response: response.json()['result'] == 'OK',
    poke_interval=5,
    dag=dag
)

getResultAndSave = PythonOperator(
    task_id="get_result_and_save",
    python_callable=getResultAndSave,
    dag=dag
)


fetchDataToLocal >> invokeTransformOperator >> sensorTransformCompleted >> getResultAndSave