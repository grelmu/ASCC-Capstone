import os
import sys
from threading import local
import typing
import fastapi
from fastapi import APIRouter, Depends, Security, status, HTTPException
from fastapi.security import SecurityScopes, OAuth2PasswordRequestForm, OAuth2PasswordBearer

import pydantic
import json
import bson

import passlib.pwd
import passlib.context
import jose.jwt

from datetime import datetime, timedelta

from mppw import logger
from . import storage
from .storage import app_model_storage_layer
from . import models
from .models import request_repo_layer

LOCAL_JWT_ALGORITHM = "HS256"
LOCAL_ACCESS_TOKEN_EXPIRE_MINUTES = 300
LOCAL_TOKEN_ENDPOINT = "token"

ADMIN_SCOPE, ADMIN_SCOPE_NAME = "*", "Admin Scope"
PROVENANCE_SCOPE, PROVENANCE_SCOPE_NAME = "provenance", "Provenance Scope"

SCOPES = {
    ADMIN_SCOPE: ADMIN_SCOPE_NAME,
    PROVENANCE_SCOPE: PROVENANCE_SCOPE_NAME
}

def create_router(app):

    router = APIRouter(prefix="/api/security")

    #
    # Initialize secrets
    #

    password_context = passlib.context.CryptContext(schemes=["bcrypt"], deprecated="auto")

    @router.on_event('startup')
    def init_admin_user():

        logger.info("Ensuring admin user...")

        with app_model_storage_layer(app).start_session() as session:
            
            user_repo = models.UserRepository(session)

            admin_username = os.environ.get("MPPW_ADMIN_USERNAME") or app_model_storage_layer(app).get_admin_username()
            if not admin_username:
                raise Exception(f"Cannot infer admin username, please specify MPPW_ADMIN_USERNAME env variable")
            
            admin_user = user_repo.query(username=admin_username)
            if admin_user is not None: return admin_user

            admin_password = os.environ.get("MPPW_ADMIN_PASSWORD") or app_model_storage_layer(app).get_admin_password()
            if not admin_password:
                raise Exception(f"Cannot infer admin password, please specify MPPW_ADMIN_PASSWORD env variable")

            admin_user = models.User(username=admin_username,
                                     hashed_password=password_context.hash(admin_password),)

            user_repo.create(admin_user)

    @router.on_event('startup')
    def init_jwt_secret_key():

        logger.info("Ensuring JWT secret key...")

        with app_model_storage_layer(app).start_session() as session:
            
            kv_repo = models.ConfigKvRepository(session)

            jwt_key_key = "%s.local_jwt_secret_key" % __name__
            init_app_local_jwt_secret_key(app, kv_repo.setdefault(jwt_key_key, passlib.pwd.genword(length=32, charset="hex")))

    #
    # Local authentication 
    #

    def local_authenticate_user(username, password, user_repo):
        user = user_repo.query(username=username)
        if not user: return False
        print(user, flush=True)
        if not password_context.verify(password, user.hashed_password): return False
        return user

    #
    # Local authorization
    #

    def local_authorize_scopes(user, scopes, user_repo):
        return True

    #
    # Local OAuth password bearer token dependencies
    #

    token_endpoint = "%s/%s" % (router.prefix, LOCAL_TOKEN_ENDPOINT)
    local_oauth2_scheme = OAuth2PasswordBearer(tokenUrl=token_endpoint, scopes=SCOPES)

    def get_current_user(security_scopes: SecurityScopes,
                         token: str = Depends(local_oauth2_scheme)):
        
        if security_scopes.scopes:
            authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
        else:
            authenticate_value = f"Bearer"
        
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": authenticate_value},
        )

        permissions_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not enough permissions",
            headers={"WWW-Authenticate": authenticate_value},
        )
        
        safe_user: SafeUser = None
        user_scopes = []
        try:
            payload = decode_local_access_token(token, app_local_jwt_secret_key(app))
            safe_user = payload.get("user")
            user_scopes = payload.get("scopes")
        except jose.JWTError as ex:
            raise credentials_exception

        if safe_user is None:
            raise credentials_exception

        if ADMIN_SCOPE in user_scopes:
            return safe_user

        for scope in security_scopes.scopes:
            if scope not in user_scopes:
                raise permissions_exception

        return safe_user

    def get_current_active_user(current_user: models.User = Security(get_current_user)):
        #if current_user.disabled:
        #    raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        return current_user

    init_request_user(app, get_current_active_user)

    #
    # Security endpoints
    #

    class Token(pydantic.BaseModel):
        access_token: str
        token_type: str

    class SafeUser(pydantic.BaseModel):
        id: typing.Optional[models.PyObjectId]
        username: str

        class Config:
            json_encoders = {
                bson.ObjectId: str
            }
        
    @router.post("/" + LOCAL_TOKEN_ENDPOINT, response_model=Token)
    def post_login_for_local_access_token(form_data: OAuth2PasswordRequestForm = Depends(OAuth2PasswordRequestForm),
                                          repo_layer: models.RepositoryLayer = Depends(request_repo_layer(app))):

        user_repo = repo_layer.get(models.UserRepository)
        user = local_authenticate_user(form_data.username, form_data.password, user_repo)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not local_authorize_scopes(user, form_data.scopes, user_repo):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cannot authorize selected scopes",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = encode_local_access_token({
            "sub": user.username,
            "user": json.loads(SafeUser(**user.dict()).json()),
            "scopes": form_data.scopes}, app_local_jwt_secret_key(app))

        return {"access_token": access_token, "token_type": "bearer"}

    @router.get("/users/me/", response_model=SafeUser)
    def get_users_me(current_user: models.User = Security(request_user(app))):
        return current_user

    @router.get("/users/", response_model=typing.List[SafeUser])
    def get_all_users(current_user: models.User = Security(request_user(app), scopes=[ADMIN_SCOPE_NAME]),
                      repo_layer: models.RepositoryLayer = Depends(request_repo_layer(app))):
        
        user_repo = repo_layer.get(models.UserRepository)
        return list(map(lambda u: SafeUser(**u.dict()), user_repo.query()))
        
    return router

def init_request_user(app: fastapi.FastAPI, get_request_user):
    app.state.security_request_user = get_request_user

def request_user(app: fastapi.FastAPI):
    return app.state.security_request_user

def init_app_local_jwt_secret_key(app: fastapi.FastAPI, local_jwt_secret_key):
    app.state.security_local_jwt_secret_key = local_jwt_secret_key

def app_local_jwt_secret_key(app: fastapi.FastAPI):
    return app.state.security_local_jwt_secret_key

#
# Utilities
#

def encode_local_access_token(data: dict, jwt_secret_key: str, expires_delta=timedelta(minutes=LOCAL_ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jose.jwt.encode(to_encode, jwt_secret_key, algorithm=LOCAL_JWT_ALGORITHM)
    return encoded_jwt

def decode_local_access_token(token_jwt: str, jwt_secret_key: str):
    return jose.jwt.decode(token_jwt, jwt_secret_key, algorithms=[LOCAL_JWT_ALGORITHM])

def encode_pagination_token(*args, **kwargs):
    return encode_local_access_token(*args, **kwargs)

def decode_pagination_token(*args, **kwargs):
    return decode_local_access_token(*args, **kwargs)    
