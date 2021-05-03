# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Keycloak authentication backend"""
from functools import wraps
from typing import Callable, Optional, Tuple, TypeVar, Union, cast
from flask import Response, current_app, request
from flask_appbuilder.security.sqla.models import User
from flask_login import login_user
from requests.auth import AuthBase

import requests
import json

CLIENT_AUTH: Optional[Union[Tuple[str, str], AuthBase]] = None


def init_app(_):
    """Initializes authentication backend"""


T = TypeVar("T", bound=Callable)  # pylint: disable=invalid-name


def auth_current_user() -> Optional[User]:
    print("\n## 1. keycloak_auth.auth_current_user() ")
    """Authenticate and set current user if Authorization header exists"""
    auth = request.authorization
    print(f"\n## 2. keycloak_auth.auth_current_user() => request.authorization: {auth} ")
	
    #if auth is None or not auth.username or not auth.password:
    if auth is None or ((not 'access_token' in auth or not 'token' in auth) and (not 'username' in auth and not 'password' in auth)):
        print(f"\n## 2.5 FAILED AUTH - NO MANDATORY PARAMETERS: (username + password | token | access_token ) \n\n")
        return None

    ab_security_manager = current_app.appbuilder.sm
    user = None
    if user is None:
        oauth_providers = ab_security_manager.getOauthParams()
        if not 'access_token' in auth and not 'token' in auth:
            url = oauth_providers["access_token_url"]
            reqToken = {'client_id': oauth_providers["client_id"], 
            			'client_secret': oauth_providers["client_secret"],
            			'username': auth.username,
            			'password': auth.password,
            			'grant_type': 'password'}
            resToken = requests.post(url, data = reqToken)
            resTokenJSON = json.loads(resToken.text)
            access_token = resTokenJSON['access_token']
            print(f"\n## 3.A  access_token NOT in auth (called oauth) => {access_token}")
        else:
            print(f"\n## 3.B  access_token/token in auth => {auth}")
            access_token = auth.access_token if 'access_token' in auth else auth.token

        url = oauth_providers["api_base_url"] + "userinfo"
        reqUserinfo = {'access_token': access_token}
        resUserinfo = requests.post(url, data = reqUserinfo)
        resUserinfoJSON = json.loads(resUserinfo.text)
        print(f"\n\n## 4. USERINFO is => {resUserinfoJSON}")
        resUserinfoJSON['username'] = resUserinfoJSON['preferred_username']
        
        user = ab_security_manager.auth_user_oauth(resUserinfoJSON)
        print(f"\n## 5. keycloak_auth.auth_user_oauth() user is => {user} \n")
    if user is not None:
        login_user(user, remember=False)
    return user


def requires_authentication(function: T):
    """Decorator for functions that require authentication"""

    @wraps(function)
    def decorated(*args, **kwargs):
        if auth_current_user() is not None:
            return function(*args, **kwargs)
        else:
            return Response("Unauthorized", 401, {"WWW-Authenticate": "Basic"})

    return cast(T, decorated)
