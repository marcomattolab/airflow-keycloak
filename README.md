# Controller (Airflow)
This repository contains the docker-compose used by the Controller (Airflow) secured by Keycloak IDM.
The docker-compose uses as internal components these 3: Airflow as Controller, Keycloak as IDM, PostgreSQL as meta-data storage DBMS.


## Table of Contents
1. [Docker](#docker)
2. [Docker-compose](#docker-compose)
3. [Configuration](#configuration)
4. [Development](#development)
    1. [DAG](#dag)
    1. [RESTFull APIs](#restfull-apis)
    1. [Workflow Lifecycle](#workflow-lifecycle)
4. [License](#license)


## Docker

Build docker image:

```bash
$ docker-compose build
```

Run docker image:

```bash
$ docker-compose up -d
```

## Docker-compose
The provided docker-compose.yml build and deploy the application with an instance of the IDM (Keycloak).

Run the following command to use the docker-compose:


```bash
$ cd airflow-keycloak
$ docker-compose up
```

## Configuration
This section summarizes the basic steps for first configurations needed to integrate controller (Airflow) and IDM (Keycloak) into the ecosystem.

1. Modify (if necessary - See docker-compose, airflow.cfg, webserver_config.py for host and port specifications: keycloak:8080, airflow:8280
2. Start container docker
2. Create manually realm 'airflow' (if needed) on http://keycloak:8080/
3. Execute script to create groups/roles into keycloak docker istance (if needed - See [import-realm-data])
4. Test Airflow is UP/RUNNING on http://airflow:8280/

## Development

This section summarizes the key concepts related to the controller (Airflow) and how develop a workflow in term of Restfull API needed to be available in the ecosystem AI/ML components.


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

## Workflow Lifecycle

This section summarizes the Controller Workflow Lifecycle (5 phases):

| Phase Name| Tool | Phase Description |
| :--- | :--- | :--- |
| Design | IDE | Creation/Change of workflow with an external Python IDE |
| Deploy | SSH | Deployment of workflow, python file, inside a specific folder into the controller |
| Run | Controller | Execution of workflow invoked manually by UI or by Restfull API |
| Monitoring | Controller | Monitoring of logs, metadata and outputs based on UI |

## License

[Apache License, Version 2.0](LICENSE.md)
