# Company: Engineering Ingegneria Informatica S.p.A.
# Class: keycloak_auth.py 
# Description: 
#    This is the authentication backend working as authenticator with Keycloak (IDM).
#    The authentication backend uses a valid "Bearer" token (if provided in headers/authorization) 
#    otherwise uses credentials: username and password  (if provided in request/authorization)
#
# License: http://www.apache.org/licenses/LICENSE-2.0
#
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
    print(f"\n## 2. keycloak_auth.auth_current_user() => request.authorization: {request.authorization}  -  request.headers.get('Authorization'): {request.headers.get('Authorization')} ")
    bearer_array = request.headers.get('Authorization').split(" ") if request.headers.get('Authorization') is not None else []
    bearer = bearer_array[1] if len(bearer_array)==2 and bearer_array[0]=="Bearer" else None
    
    if bearer is None and not 'username' in auth and not 'password' in auth:
        print(f"\n## 2.5 FAILED AUTH - NO MANDATORY PARAMETERS: (username and password | Bearer ) ")
        return None

    ab_security_manager = current_app.appbuilder.sm
    user = None
    if user is None:
        oauth_providers = ab_security_manager.getOauthParams()
        if bearer is None:
            url = oauth_providers["access_token_url"]
            reqToken = {'client_id': oauth_providers["client_id"], 
            			'client_secret': oauth_providers["client_secret"],
            			'username': auth.username,
            			'password': auth.password,
            			'grant_type': 'password'}
            resToken = requests.post(url, data = reqToken)
            resTokenJSON = json.loads(resToken.text)
            access_token = resTokenJSON['access_token']
            print(f"\n## 3.A  access_token retrieved from keycloak (IDM) by credentials => {access_token}")
        else:
            print(f"\n## 3.B  access_token equals to Bearer retrieved from headers => {bearer}")
            access_token = bearer

        url = oauth_providers["api_base_url"] + "userinfo"
        reqUserinfo = {'access_token': access_token}
        resUserinfo = requests.post(url, data = reqUserinfo)
        resUserinfoJSON = json.loads(resUserinfo.text)
        print(f"\n\n## 4. USERINFO (Json) retrieved => {resUserinfoJSON}")
        resUserinfoJSON['username'] = resUserinfoJSON['preferred_username']
        
        user = ab_security_manager.auth_user_oauth(resUserinfoJSON)
        print(f"\n## 5. keycloak_auth.auth_user_oauth() authenticated user is => {user} ")
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
