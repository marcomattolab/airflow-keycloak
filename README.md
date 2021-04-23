# Controller (Airflow)
This repository contains the docker-compose used by the Controller (Airflow) secured by Keycloak IDM.
The docker-compose uses as internal components these 3: Airflow as Controller, Keycloak as IDM, PostgreSQL as meta-data storage DBMS.


## Table of Contents
1. [Docker](#docker)
1. [Configuration](#configuration)
    1. [DAG](#dag)
    1. [RESTFull APIs](#apis)
1. [License](#license)


## Docker

Build docker image:

```bash
$ docker-compose build
```

Run docker image:

```bash
$ docker-compose up -d
```

## First Configuration
1. Modify (if necessary - See docker-compose, airflow.cfg host and ports: keycloak:8080, airflow:8280
2. Start container docker
2. Create manually realm 'airflow' (if needed) on http://keycloak:8080/
3. Execute script to create groups/roles into keycloak docker istance (if needed - See [import-realm-data])
4. Test Airflow is UP/RUNNING on http://airflow:8280/

### DAG 
Create a DAG (Directed Acyclic Graph), a file python (ex. "component_one.py"), for each ML/AI component that should be integrated in the controller (put this file inside the directory "dags" to deploy/validate file).

See example DAG: urbanite_data_poc_final2.py

### RESTFull APIs
Each ML/AI component to be integrated in the "logic" of DAG created at the step before, should implement these APIs:

| HTTP| NAME | DESCRIPTION |
| :--- | :--- | :--- |
| `GET` | status | `This API invokes the target system to get status (in progress, completed, ..) of the long-term execution based on field “executionid” (id provided by controller and assigned to elaboration/execution). Input: json with a field “executionid”.  Output: json with a field “result“ with values “OK”, “KO”, “PENDING”.` |
| `POST` | job | `This API invokes a long-term execution (ML / AI algorithm) into the target system. Input: json with a field “executionid”, plus other inputs (if required by AI/ML component). Output: json with a field “result“ with values “OK”, “KO”.` |
| `GET` | result | `This API invokes the target system, after that elaboration has been succesfully completed, to get localtion of results: Input: json with a field “executionid”. Output: json with a field indication location of result.` |

An example is "urbanite_data_poc_final2.py" in which a DAG invokes API of a generic component (AI/ML) using base operators (HTTPSensor, HTTPOperator).

So the Controller invokes respectivelly:
- API "job" => to start a long-term execution in the AI/ML component by http/operator.
- API "status" => to get periodically "status" of the long-term execution by http/sensor.
- API "result" => to get the "location" of the result when AI/ML component has been completed long-term execution.


## License

[Apache License, Version 2.0](LICENSE.md)
