### Running

```
docker-compose build

docker-compose up -d
```


### Using API
Enable basic auth for API by setting airflow.cfg
```
auth_backend = airflow.api.auth.backend.basic_auth
```

List Dags

```
curl -u admin -X GET "http://localhost:8080/api/v1/dags?limit=50" -H  "accept: application/json"
```

View a Specific Dag
```
curl -u admin:admin -X GET "http://localhost:8080/api/v1/dags/process_etl_linear"
```

Patch a Dag

```
curl -u admin:admin -H"Content-Type: application/json" -X PATCH "http://localhost:8080/api/v1/dags/process_etl_linear" -d '{
  "is_paused": false
}'
```

Run a Dag

```
curl -u admin:admin -X POST "http://localhost:8080/api/v1/dags/process_etl_linear/dagRuns"  \
-H"Content-Type: application/json" -d '{
  "conf": {},
  "dag_run_id": "2020_11_23_2_21_00",
  "execution_date": "2020-11-22T15:13:15.022Z"  
}'
```


### Securing with Keycloak

Import airflow-realm.json as a realm in keycloak. docker-compose.yaml also mounts manager.py whose ```get_oauth_user_info``` has been update in the following way:

```
        else:
            me = self.appbuilder.sm.oauth_remotes[provider].get("userinfo")
            data = me.json()
            log.debug("User info from OAuth Provider: {0}".format(data))
            return {
                "preferred_username": data.get("preferred_username",""),
                "first_name": data.get("given_name", ""),
                "last_name": data.get("family_name", ""),
                "email": data.get("email", ""),
                "name": data.get("name", ""),
                "username": data.get("preferred_username", ""),
                "id": data.get("sub", ""),
                "roles": data.get("roles", [])
            }
```

Note, if using keycloak <= 11.x, roles need to be configured

webserver_config.py is also mounted from outside to have the effective value of

```
from flask_appbuilder.security.manager import AUTH_OAUTH
AUTH_TYPE = AUTH_OAUTH

AUTH_ROLE_ADMIN = 'Admin'

AUTH_ROLE_PUBLIC = 'Public'

AUTH_USER_REGISTRATION = True

#Do not disable this in production
OIDC_COOKIE_SECURE = False

OAUTH_PROVIDERS = [
 {
   'name': 'airflow-client',
   'icon': 'fa-key',
   'token_key': 'access_token', 
   'remote_app': {
     'api_base_url': 'http://keycloak:8080/auth/realms/airflow/protocol/openid-connect/',
     'client_kwargs': {
       'scope': 'openid'
     },
     'request_token_url': None,
     'access_token_url': 'http://keycloak:8080/auth/realms/airflow/protocol/openid-connect/token',
     'authorize_url': 'http://keycloak:8080/auth/realms/airflow/protocol/openid-connect/auth',
     'client_id': 'airflow-client',
     'client_secret': '9e661802-3356-44f3-8960-1dc890abd2bc'
    }
  }
]

```

keycloak's airflow realm can be found in airflow-realm.json

#### Testing OAuth Integration
```
docker-compose up -d
```

update /etc/hosts with the following entry
```
127.0.0.1   airflow keycloak
```

#### Import realm data

```
docker exec -it <airflow_keycloak_id> /bin/bash

#run the following to import keycloak data

export KEYCLOAK_HOME=/opt/jboss/keycloak
export PATH=$PATH:$KEYCLOAK_HOME/bin

kcadm.sh config credentials --server http://localhost:8080/auth --realm master --user admin --password admin

kcadm.sh create realms -f /tmp/realms/airflow-realm-data.json
kcadm.sh create client-scopes -r airflow -f /tmp/realms/client-scopes/scope1.json
kcadm.sh create clients -r airflow -f /tmp/realms/clients/single-client.json

kcadm.sh create roles -r airflow -f /tmp/realms/roles/role1.json
kcadm.sh create roles -r airflow -f /tmp/realms/roles/role2.json
kcadm.sh create roles -r airflow -f /tmp/realms/roles/role3.json
kcadm.sh create roles -r airflow -f /tmp/realms/roles/role4.json

kcadm.sh create users -r airflow -f /tmp/realms/users/user2.json
user_id=$(kcadm.sh get users -r airflow|grep airflow -C 3|grep "id"|awk -F" " '{print $3}'|sed s/,//g|sed s/\"//g)
kcadm.sh update users/${user_id}/reset-password -r airflow -s type=password -s value=airflow -s temporary=false -n


role_id=$(kcadm.sh get roles -r airflow|grep Admin -C 2|grep "id"|awk -F" " '{print $3}'|sed s/,//g|sed s/\"//g)
sed s/__ID__/${role_id}/ /tmp/realms/client-scopes/mapping_template.json|tee /tmp/realms/client-scopes/mappings.json
kcadm.sh create client-scopes/025074e3-3874-4263-b026-489587d3417f/scope-mappings/realm -r airflow -f /tmp/realms/client-scopes/mappings.json
kcadm.sh create users/${user_id}/role-mappings/realm -r airflow -f /tmp/realms/client-scopes/mappings.json

```

#### Verification

```

Verify that Admin, Public, User are effective roles in the keycloak Default Client Scope 
http://localhost:8080/auth/admin/master/console/#/realms/airflow/client-scopes/025074e3-3874-4263-b026-489587d3417f/scope-mappings

Verify that User Airflow is assigned Admin,Public,User role
http://localhost:8080/auth/admin/master/console/#/realms/airflow/users/9e41a8d4-ea41-471e-b194-018465d3df66/role-mappings

```

Test your OAuth connectivity using:
open http://airflow:8280/



#### Export Realm Data
```
docker exec -it airflow_keycloak_1 bash


#run the following to export keycloak data

export KEYCLOAK_HOME=/opt/jboss/keycloak
export PATH=$PATH:$KEYCLOAK_HOME/bin

kcadm.sh config credentials --server http://localhost:8080/auth --realm master --user admin --password admin


kcadm.sh get realms/airflow > /tmp/realms/airflow-realm-data.json
kcadm.sh get clients -r airflow > /tmp/realms/airflow-clients.json
kcadm.sh get roles -r airflow > /tmp/realms/airflow-roles.json
kcadm.sh get users -r airflow > /tmp/realms/airflow-users.json
kcadm.sh get users -r airflow > /tmp/realms/airflow-users.json
kcadm.sh get serverinfo -r airflow > /tmp/realms/airflow-server-info.json
kcadm.sh get client-scopes -r airflow > /tmp/realms/airflow-client-scopes.json 

```


#### Resources
See keycloak: https://www.keycloak.org/getting-started/getting-started-docker

See source: https://github.com/skhatri/airflow-by-example

#### Usefull docker commands
```
Path Airflow static resources => /home/airflow/.local/lib/python3.8/site-packages/airflow/www/static

Copy folder from cointer to external volume =>  docker cp <548>:/home/airflow/.local/lib/python3.8/site-packages/airflow/www/static ./static

Copy file from cointer to external file => docker cp <548>:/home/airflow/.local/lib/python3.8/site-packages/airflow/www/templates/appbuilder/navbar.html .

Copy file from cointer to external file => docker cp <548>:/opt/airflow/airflow.cfg .
Copy file from cointer to external file => docker cp <548>:/opt/airflow/webserver_config.py .
Copy file from cointer to external file => docker cp <548>:/home/airflow/.local/lib/python3.8/site-packages/flask_appbuilder/security/manager.py .

```

#### My Suggestions
1. Modify file host (docker-compose.yaml, airflow.cfg, navbar_right.html)
2. Start docker container
2. Create realm 'airflow' manually on http://localhost:8080
3. Execute script to create groups/roles into keycloak docker istance (as described below)
4. Test http://airflow:8280/
