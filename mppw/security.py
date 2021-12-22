import os
import sys
import typing
from fastapi import APIRouter, Depends, Security, status, HTTPException
from fastapi.security import SecurityScopes, OAuth2PasswordRequestForm, OAuth2PasswordBearer

import pydantic
import passlib.pwd
import passlib.context
import jose.jwt
from sqlmodel import Session

from datetime import datetime, timedelta

from mppw import logger
from . import models
from . import storage

LOCAL_JWT_ALGORITHM = "HS256"
LOCAL_ACCESS_TOKEN_EXPIRE_MINUTES = 300
LOCAL_TOKEN_ENDPOINT = "token"

ADMIN_SCOPE_NAME = "*"

SCOPES = {
    ADMIN_SCOPE_NAME: "Admin Scope"
}

def create_router(app):

    router = APIRouter(prefix="/security")

    #
    # Initialize secrets
    #

    password_context = passlib.context.CryptContext(schemes=["bcrypt"], deprecated="auto")

    @router.on_event('startup')
    def init_admin_user():

        logger.info("Ensuring admin user...")

        with Session(app.state.model_storage_layer.engine) as session:
            
            user_repo = models.UserRepository(session)

            admin_username = os.environ.get("ADMIN_USERNAME", "admin")
            admin_user = user_repo.get_user_by_username(admin_username)
            if admin_user is not None: return admin_user 

            admin_password = os.environ.get("ADMIN_PASSWORD", None)
            if admin_password is None:
                admin_password = passlib.pwd.genword(entropy="secure", charset="hex")
                admin_password_file = os.environ.get("ADMIN_PASSWORD_FILE", ".admin_password")
                with open(admin_password_file, 'w') as f:
                    f.write(admin_password)
            
            admin_user = models.User(username=admin_username,
                                     hashed_password=password_context.hash(admin_password),)

            user_repo.create_user(admin_user)

    @router.on_event('startup')
    def init_jwt_secret_key():

        logger.info("Ensuring JWT secret key...")

        with Session(app.state.model_storage_layer.engine) as session:
            
            kv_repo = models.ConfigKvRepository(session)

            jwt_key_key = "%s.local_jwt_secret_key" % __name__
            app.state.local_jwt_secret_key = kv_repo.setdefault(jwt_key_key, passlib.pwd.genword(length=32, charset="hex")).value

    #
    # Local authentication 
    #

    def local_authenticate_user(username, password, user_repo):
        user = user_repo.get_user_by_username(username)
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
            payload = decode_local_access_token(token, app.state.local_jwt_secret_key)
            safe_user = payload.get("sub")
            user_scopes = payload.get("scopes")
        except jose.JWTError:
            raise credentials_exception

        if safe_user is None:
            raise credentials_exception

        if ADMIN_SCOPE_NAME in user_scopes:
            return safe_user

        for scope in security_scopes.scopes:
            if scope not in user_scopes:
                raise permissions_exception

        return safe_user

    def get_current_active_user(current_user: models.User = Security(get_current_user)):
        if current_user.disabled:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        return current_user

    app.state.request_current_active_user = get_current_active_user

    #
    # Security endpoints
    #

    class Token(pydantic.BaseModel):
        access_token: str
        token_type: str

    class SafeUser(pydantic.BaseModel):
        id: typing.Optional[int]
        username: str
        
    @router.post("/" + LOCAL_TOKEN_ENDPOINT, response_model=Token)
    def post_login_for_local_access_token(form_data: OAuth2PasswordRequestForm = Depends(OAuth2PasswordRequestForm),
                                          repo_layer: models.RepositoryLayer = Depends(app.state.request_repo_layer)):

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

        access_token = encode_local_access_token({"sub": SafeUser(user), "scopes": form_data.scopes}, app.state.local_jwt_secret_key)
        return {"access_token": access_token, "token_type": "bearer"}

    @router.get("/users/me/", response_model=SafeUser)
    def get_users_me(current_user: models.User = Security(get_current_active_user)):
        return current_user

    @router.get("/users/", response_model=typing.List[SafeUser])
    def get_users_me(current_user: models.User = Security(get_current_active_user)):
        return current_user

    app.include_router(router)

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
