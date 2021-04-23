import requests
import json
import pickle
from decimal import Decimal
import pandas as pd
import psycopg2 as pg
from datetime import date
from configparser import ConfigParser
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
from airflow.models import Variable
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.models.baseoperator import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.exceptions import AirflowException

#TODO Define Variables and Connections
#ETL_NAME = Variable.get ("ETL_NAME_ES")
#SAVE_DATA = Variable.get ("ETL_SAVE_DATA_ES")
#ETL_URL = Variable.get ("ETL_URL_ES")

#See http://api.citybik.es/v2/
CURRENT_TIMESTAMP = datetime.now()
ETL_NAME = "api.citybik.es"
SAVE_DATA = True
ETL_URL = "https://api.citybik.es/v2/networks/bilbon-bizi"


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
    df.to_json("/opt/airflow/logs/urbanite_data_{}.json".format(date.today().strftime("%Y%m%d")))


#############################################################################
# Transform : Add Field And Save
#############################################################################
def addFieldAndSave():
    """
    we make the connection to postgres using the psycopg2 library, create
    the schema to hold data, and insert from the local json file
    """

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
    
    # create the table if it does not already exist
    if SAVE_DATA:
        cursor = dbconnect.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS urbanite_data_perc (
                etlname VARCHAR(1000),
                etltimestamp TIMESTAMP without time zone,
                id VARCHAR(1000),
                timestamp VARCHAR(1000),
                name VARCHAR(1000),
                latitude VARCHAR(1000),
                longitude VARCHAR(1000),
                slots INT,
                empty_slots INT,
                free_bikes INT,
                number INT,
                free_bikes_perc numeric,
                PRIMARY KEY (etlname, etltimestamp, id)
            );
            
        """
        )
        dbconnect.commit()

    with open("/opt/airflow/logs/urbanite_data_{}.json".format(date.today().strftime("%Y%m%d"))) as f:
        data = json.load(f)
        print(data)

        stationsArray = data["network"]["stations"]
        for i in range(len(stationsArray)):
            id = stationsArray[i]['id']
            name = stationsArray[i]['name']
            timestamp = stationsArray[i]['timestamp']
            latitude = stationsArray[i]['latitude']
            longitude = stationsArray[i]['longitude']
            free_bikes = stationsArray[i]['free_bikes']
            empty_slots = stationsArray[i]['empty_slots']
            bike_uids = stationsArray[i]['extra']['bike_uids']
            uid = stationsArray[i]['extra']['uid']
            number = stationsArray[i]['extra']['number']
            slots = stationsArray[i]['extra']['slots']

            # This is the transformation just to have the in free_bikes_percentage
            free_bikes_perc = stationsArray[i]['free_bikes'] / stationsArray[i]['extra']['slots'] if (free_bikes < slots) else 1
            print("id: {} free_bikes_perc: {}".format(id, free_bikes_perc))

            if SAVE_DATA:
                # print("INSERT INTO urbanite_data_perc VALUES ('{}', '{}', '{}', '{}', '{}','{}', '{}', '{}', '{}', '{}' , '{}', '{}')".format(ETL_NAME, CURRENT_TIMESTAMP, id, timestamp, name, latitude, longitude, slots, empty_slots, free_bikes, number, free_bikes_perc))
                cursor.execute("""
                INSERT INTO urbanite_data_perc
                VALUES ('{}', '{}', '{}', '{}','{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}')
                """.format(ETL_NAME, CURRENT_TIMESTAMP, id, timestamp, name, latitude, longitude, slots, empty_slots, free_bikes, number, free_bikes_perc)
                )
        if SAVE_DATA :
            dbconnect.commit()

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
        with open("/opt/airflow/logs/urbanite_data_generated_{}.json".format(date.today().strftime("%Y%m%d")), 'w') as file:
            file.write(json.dumps(jsonTotalDistribution, cls=CustomJsonEncoder))
        
        print("URBANITE:= Algorithm has been successfully completed and file generated!!!")



default_args={
    "owner": "airflow", 
    "start_date": datetime.today() - timedelta(days=1)
}

dag = DAG(
    "urbanite_data_poc_advanced",
    default_args=default_args,
    schedule_interval="*/15 * * * *"
)
dag.doc_md = __doc__


fetchDataToLocal = PythonOperator(
    task_id="fetch_data_to_local",
    python_callable=fetchDataToLocal,
    dag=dag
)
fetchDataToLocal.doc_md = """\
Documentation: This task do a fetch_data_to_local !!!!!!!!!!!
"""


addFieldAndSave = PythonOperator(
    task_id="add_new_field_and_save",
    python_callable=addFieldAndSave,
    dag=dag
)
addFieldAndSave.doc_md = """\
Documentation: This task do a addFieldAndSave !!!!!!!!!!!
"""


categorizeResultAndSave = PythonOperator(
    task_id="categorize_result_and_save",
    python_callable=categorizeResultAndSave,
    dag=dag
)
categorizeResultAndSave.doc_md = """\
Documentation: This task do a categorizeResultAndSave !!!!!!!!!!!
"""


fetchDataToLocal >> addFieldAndSave >> categorizeResultAndSave