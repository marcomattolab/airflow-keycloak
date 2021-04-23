from airflow import DAG
from airflow.decorators import task, dag

from datetime import datetime
import pandas as pd

@task
def extract():

    people = {
        'Firstnames': ['James','Corolla','Mark','Eddy'],
        'Lastnames': ['Wick','Leto','Smith','Etwan']
    }

    df = pd.DataFrame(people, columns = ['Firstnames', 'Lastnames'])
    #return df
    return people
    

@task
def process(value):
    print(f"Processing: {value}")

@dag(schedule_interval='@daily', start_date=datetime(2021, 1, 1), catchup=False)
def my_dag():

    value = extract()
    process(value)

dag = my_dag()