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


#Variables
#ETL_NAME = Variable.get ("ETL_NAME_ES")
#SAVE_DATA = Variable.get ("ETL_SAVE_DATA_ES")
#ETL_URL = Variable.get ("ETL_URL_ES")

#See http://api.citybik.es/v2/
#execution_date = datetime.now()
ETL_NAME = "api.citybik.es"
SAVE_DATA = True
ETL_URL = "https://api.citybik.es/v2/networks/bilbon-bizi"
#myuuid = uuid.uuid4()

#https://medium.com/leboncoin-engineering-blog/data-traffic-control-with-apache-airflow-ab8fd3fc8638
#https://airflow.apache.org/docs/apache-airflow/stable/macros-ref.html
#https://towardsdatascience.com/elementals-of-airflow-part-1-6e4ce1de4dfb

#############################################################################
# CustomJsonEncoder
#############################################################################
class CustomJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(CustomJsonEncoder, self).default(obj)


#############################################################################
# GET / Extract and fetch Data To Local
#############################################################################
def fetchDataToLocal():
    """
    we use the python requests library to fetch the data in json format, then
    use the pandas library to easily convert/save json file in the local data directory
    """

    # fetching the request
    response = requests.get(ETL_URL)

    # convert the response to a pandas dataframe, then save as file to the data folder in our project directory
    df = pd.DataFrame(json.loads(response.content))

    # for integrity reasons, let's attach the current date to the filename
    df.to_json("/opt/airflow/logs/urbanite_data_{}.json".format(datetime.today().strftime("%Y%m%d")))
    #print("URBANITE:= Start execution_date: '{}' is in progress".format(execution_date))
    context = get_current_context()
    uuidTime = context['ts']
    print(context['run_id'])
    print(context['ti'])
    print(context['ts'])
    print("URBANITE:= Start uuidTime: '{}' is in progress".format(uuidTime))


#############################################################################
# Get Result: Categorize Result And Save File json on filesystem
#############################################################################
def categorizeResultAndSave():
    # attempt the connection to postgres
    try:
        dbconnect = pg.connect(
            database="airflow",
            user="airflow",
            password="airflow",
            host="postgres"
        )
    except Exception as error:
        print(error)

    if SAVE_DATA:
        cursor = dbconnect.cursor()
        
        lowerDistribution = []
        mediumDistribution = []
        hightDistribution = []
        jsonTotalDistribution= {"lowerDistribution": lowerDistribution,
                                "mediumDistribution": mediumDistribution,
                                "hightDistribution": hightDistribution}

        querySelect = """
            SELECT id, timestamp, name, latitude, longitude, slots, empty_slots, free_bikes, number, free_bikes_perc 
            from urbanite_data_perc 
            WHERE etlname = '{}' 
            and etltimestamp = (select max(etltimestamp) from urbanite_data_perc where etlname = '{}' ) 
            and free_bikes_perc > {} 
            and free_bikes_perc <= {};
            """

        # Select for lowerDistribution (1)
        cursor.execute(querySelect.format(ETL_NAME, ETL_NAME, 0, 0.3))
        sources = cursor.fetchall()
        for source in sources:
            source_ = {"id": source[0], "timestamp": source[1], "name": source[2], "latitude": source[3],
                       "longitude": source[4], "slots": source[5], "empty_slots": source[6], "free_bikes": source[7],
                       "number": source[8], "free_bikes_perc": source[9]}
            jsonTotalDistribution['lowerDistribution'].append(source_);
            print(" lowerDistribution ==>  '{}', '{}', '{}', '{}', '{}','{}', '{}', '{}')".format(source[0],source[1],source[2],source[3],source[4],source[5],source[6],source[7]))

        # Select for mediumDistribution (2)
        cursor.execute(querySelect.format(ETL_NAME, ETL_NAME, 0.3, 0.6))
        sources = cursor.fetchall()
        for source in sources:
            source_ = {"id": source[0], "timestamp": source[1], "name": source[2], "latitude": source[3],
                       "longitude": source[4], "slots": source[5], "empty_slots": source[6], "free_bikes": source[7],
                       "number": source[8], "free_bikes_perc": source[9]}
            jsonTotalDistribution['mediumDistribution'].append(source_);
            print(" mediumDistribution ==>  '{}', '{}', '{}', '{}', '{}','{}', '{}', '{}')".format(source[0],source[1],source[2],source[3],source[4],source[5],source[6],source[7]))

        # Select for hightDistribution (3)
        cursor.execute(querySelect.format(ETL_NAME, ETL_NAME, 0.6, 1))
        sources = cursor.fetchall()
        for source in sources:
            source_ = {"id": source[0], "timestamp": source[1], "name": source[2], "latitude": source[3],
                       "longitude": source[4], "slots": source[5], "empty_slots": source[6], "free_bikes": source[7],
                       "number": source[8], "free_bikes_perc": source[9]}
            jsonTotalDistribution['hightDistribution'].append(source_);
            print(" hightDistribution ==>  '{}', '{}', '{}', '{}', '{}','{}', '{}', '{}')".format(source[0],source[1],source[2],source[3],source[4],source[5],source[6],source[7]))

        # Save json with distribution #
        with open("/opt/airflow/logs/urbanite_data_generated_{}.json".format(datetime.today().strftime("%Y%m%d")), 'w') as file:
            file.write(json.dumps(jsonTotalDistribution, cls=CustomJsonEncoder))

        # execution_date = context['dag_run'].execution_date
        context = get_current_context()
        print(context['run_id'])
        print(context['ti'])
        print(context['ts'])
        uuidTime = context['ts']
        print("URBANITE:= Algorithm execution_date: '{}' has been successfully completed and file generated!!!".format(uuidTime))

default_args={
    "owner": "airflow", 
    "start_date": datetime.today() - timedelta(days=1)
}

dag = DAG(
    "urbanite_data_poc_final",
    default_args=default_args,
    schedule_interval="*/45 * * * *"
)
dag.doc_md = __doc__


fetchDataToLocal = PythonOperator(
    task_id="fetch_data_to_local",
    python_callable=fetchDataToLocal,
    dag=dag
)



# The connection ID to the datawarehouse DB (must match the connection
# handler defined in airflow for the data source)
target_db = 'urbanite-db'

# A simple sensor checking wether data is present
# for the day following the execution_date of the DAG Run
sensor_query_template = '''
SELECT TRUE
FROM urbanite_data_perc
WHERE 1=1
'''

# TODO Usefull a fileSensor
# A sensor task using a SqlSensor operator
checkDataAvailSensor = SqlSensor(
    task_id='check_data_avail',
    conn_id=target_db,
    sql=sensor_query_template,
    poke_interval=10,
    timeout=60,
    dag=dag)

# See https://github.com/trbs/airflow-examples/blob/master/dags/example_http_operator.py
invokeTransformOperatorPost = SimpleHttpOperator(
    task_id='post_op',
    http_conn_id='urbinite_http',
    method='POST',
    endpoint='post-job',
    data=json.dumps({"UUID": '{{run_id}}'}),
    #data={"priority": 5, "UUID": "{{run_id}}"},
    headers={"Content-Type": "application/json"},
    #response_check=lambda response: response.json()['json']['priority'] == 5,
    #response_check=lambda response: response.json()['data']['priority'] == 5,
    response_check=lambda response: response.json()['data']['result'] == 'OK',
    #response_check=lambda response: True,
    dag=dag
)

sensorTransformCompleted = HttpSensor(
    task_id='http_sensor_check',
    http_conn_id='urbinite_http',
    endpoint='get-status',
    request_params={"_UUID": '{{run_id}}'},
    #response_check=lambda response: True,
    #response_check=lambda response: True if "Google" in response.content else True,
    #response_check=lambda response: True if "pippo" in response.text else True,
    response_check=lambda response: response.json()['data']['result'] == 'OK',
    poke_interval=5,
    dag=dag
)

categorizeResultAndSave = PythonOperator(
    task_id="categorize_result_and_save",
    python_callable=categorizeResultAndSave,
    dag=dag
)


# Template Query insert demo urbanite
aggregation_query_template_demo = '''
BEGIN;
DELETE FROM urbanite_data_perc WHERE 1=1;

INSERT INTO urbanite_data_perc VALUES 
( '{{ execution_date }}', '{{ execution_date }}', '{{ execution_date }}', 
'{{ execution_date }}', '{{ execution_date }}', '{{ execution_date }}',
'{{ run_id }}', '{{ params.example_1 }}', '234', 
'246', '257', '0.76');

'''

# A simple postgres SQL task execution
# https://stackoverflow.com/questions/44523567/airflow-pass-ds-as-param-to-postgresoperator
aggregation_task = PostgresOperator(
    task_id='aggregate_clickstream_data',
    postgres_conn_id=target_db,
    sql=aggregation_query_template_demo,
    params={'example_1':999},
    autocommit=False,
    dag=dag)



fetchDataToLocal >> checkDataAvailSensor >> invokeTransformOperatorPost >> sensorTransformCompleted >> categorizeResultAndSave >> aggregation_task