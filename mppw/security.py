import os
import sys
from threading import local
import typing
import fastapi
from fastapi import APIRouter, Depends, Security, status, HTTPException
from fastapi.security import (
    SecurityScopes,
    OAuth2PasswordRequestForm,
    OAuth2PasswordBearer,
)

import pydantic
from typing import List, Dict, Any
import json
import bson

import passlib.pwd
import passlib.context
import functools
import jose.jwt

from datetime import datetime, timedelta

from mppw import logger
from . import endpoints
from . import models
from . import repositories
from .repositories import app_storage_layer, request_repo_layer, using_app_repo_layer

LOCAL_JWT_ALGORITHM = "HS256"
LOCAL_ACCESS_TOKEN_EXPIRE_MINUTES = 300
LOCAL_TOKEN_ENDPOINT = "token"

# TODO: Move scopes to dedicated module

ADMIN_SCOPE, ADMIN_SCOPE_NAME = "*", "Admin Scope"

READ_PROVENANCE_SCOPE, READ_PROVENANCE_SCOPE_NAME = (
    "read:provenance",
    "Read Provenance Scope",
)
MODIFY_PROVENANCE_SCOPE, MODIFY_PROVENANCE_SCOPE_NAME = (
    "modify:provenance",
    "Modify Provenance Scope",
)

MODIFY_OPERATION_SCOPE, MODIFY_OPERATION_SCOPE_NAME = (
    "modify:operation",
    "Modify Operation Scope",
)
MODIFY_ARTIFACT_SCOPE, MODIFY_ARTIFACT_SCOPE_NAME = (
    "modify:artifact",
    "Modify Artifact Scope",
)

_DEPRECATED_PROVENANCE_SCOPE = "provenance"

SCOPES = {
    ADMIN_SCOPE: ADMIN_SCOPE_NAME,
    READ_PROVENANCE_SCOPE: READ_PROVENANCE_SCOPE_NAME,
    MODIFY_PROVENANCE_SCOPE: MODIFY_PROVENANCE_SCOPE_NAME,
    MODIFY_OPERATION_SCOPE: MODIFY_OPERATION_SCOPE_NAME,
    MODIFY_ARTIFACT_SCOPE: MODIFY_ARTIFACT_SCOPE_NAME,
}


def _normalize_client_scopes(client_scopes):
    normal_scopes = []
    for scope in client_scopes:
        if scope == _DEPRECATED_PROVENANCE_SCOPE or scope == MODIFY_PROVENANCE_SCOPE:
            normal_scopes.extend(
                [
                    READ_PROVENANCE_SCOPE,
                    MODIFY_PROVENANCE_SCOPE,
                    MODIFY_ARTIFACT_SCOPE,
                    MODIFY_OPERATION_SCOPE,
                ]
            )
        else:
            normal_scopes.append(scope)
    return normal_scopes


class JwtUser(models.DocModel):
    username: str


class ScopedUser(models.SafeUser):
    scopes: List[str]
    claims: Dict[str, Any]


class NewUser(models.SafeUser):
    password: str


def is_admin_user(user: models.User):
    return ADMIN_SCOPE in user.allowed_scopes


def has_admin_scope(user: ScopedUser):
    return ADMIN_SCOPE in user.scopes


def create_router(app):

    router = APIRouter(prefix="/api/security")

    #
    # Initialize secrets
    #

    @router.on_event("startup")
    def init_admin_user():

        logger.info("Ensuring admin user...")

        def ensure_admin_user(repo_layer):

            user_repo = repo_layer.users

            admin_username = (
                os.environ.get("MPPW_ADMIN_USERNAME")
                or app_storage_layer(app).get_credentials()[0]
            )
            if not admin_username:
                raise Exception(
                    f"Cannot infer admin username, please specify MPPW_ADMIN_USERNAME env variable"
                )

            admin_user = user_repo.query_one(username=admin_username)
            if admin_user is not None:
                return admin_user

            admin_password = (
                os.environ.get("MPPW_ADMIN_PASSWORD")
                or app_storage_layer(app).get_credentials()[1]
            )
            if not admin_password:
                raise Exception(
                    f"Cannot infer admin password, please specify MPPW_ADMIN_PASSWORD env variable"
                )

            admin_user = models.User(
                username=admin_username,
                hashed_password=hash_password(admin_password),
                allowed_scopes=["*"],
            )

            user_repo.create(admin_user)

        using_app_repo_layer(app, ensure_admin_user)

    @router.on_event("startup")
    def init_jwt_secret_key():

        logger.info("Ensuring JWT secret key...")

        def ensure_key(repo_layer):

            kv_repo = repo_layer.kv

            jwt_key_key = "%s.local_jwt_secret_key" % __name__
            init_app_local_jwt_secret_key(
                app,
                kv_repo.setdefault(
                    jwt_key_key, passlib.pwd.genword(length=32, charset="hex")
                ),
            )

        using_app_repo_layer(app, ensure_key)

    #
    # Local authentication
    #

    token_endpoint = "%s/%s" % (router.prefix, LOCAL_TOKEN_ENDPOINT)

    class CookifiedOAuth2PasswordBearer(OAuth2PasswordBearer):

        DEFAULT_TOKEN_COOKIE_NAME = "oauth2_token"

        def __init__(self, *args, cookie_name=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.cookie_name = (
                cookie_name or CookifiedOAuth2PasswordBearer.DEFAULT_TOKEN_COOKIE_NAME
            )

        async def __call__(self, request: fastapi.Request) -> typing.Optional[str]:
            try:
                return await super().__call__(request)
            except fastapi.HTTPException as ex:
                token = request.cookies.get(self.cookie_name)
                if not token:
                    raise ex
                return token

    local_oauth2_scheme = CookifiedOAuth2PasswordBearer(
        tokenUrl=token_endpoint, scopes=SCOPES
    )

    def local_authenticate_request_user(username, password, user_repo) -> models.User:

        user = user_repo.query_one(username=username, active=True)
        if not user:
            logger.info(f"User {username} failed to authenticate (user not found).")
            return False

        if not verify_password(password, user.hashed_password):
            logger.info(f"User {username} failed to authenticate (incorrect password).")
            return False

        logger.info(f"User {username} authenticated successfully (password).")
        return user

    def build_get_request_user(app: fastapi.FastAPI):
        @functools.lru_cache(maxsize=1024)
        def decode_token_user(token: str, app: fastapi.FastAPI):

            payload = decode_local_access_token(token, app_local_jwt_secret_key(app))
            jwt_user = JwtUser(**payload.get("user"))
            user_scopes = payload.get("scopes")

            if jwt_user is None:
                return (None, None)

            user = None

            def find_user(repo_layer):
                nonlocal user
                user_repo = repo_layer.users
                logger.warn(f"JWT user: {jwt_user}")
                user = user_repo.query_one(id=str(jwt_user.id))

            using_app_repo_layer(app, find_user)

            return (user, user_scopes)

        def get_request_user(
            required_scopes: SecurityScopes, token: str = Depends(local_oauth2_scheme)
        ):

            if required_scopes.scopes:
                authenticate_value = f'Bearer scope="{required_scopes.scope_str}"'
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

            user = None
            current_scopes = []
            try:
                user, current_scopes = decode_token_user(token, app)
            except jose.JWTError as ex:
                raise credentials_exception

            if user is None:
                raise credentials_exception

            # Upgrade any deprecated scopes
            current_scopes = _normalize_client_scopes(current_scopes)

            if ADMIN_SCOPE not in current_scopes:
                for scope in required_scopes.scopes:
                    if scope not in current_scopes:
                        raise permissions_exception

            scoped_user = ScopedUser(
                scopes=current_scopes,
                claims=dict(user.local_claims or {}),
                **user.dict(),
            )

            return scoped_user

        get_request_user.reload_claims = lambda: decode_token_user.cache_clear()

        return get_request_user

    init_request_user(app, build_get_request_user(app))

    #
    # Security endpoints
    #

    class Token(pydantic.BaseModel):
        access_token: str
        token_type: str

    @router.post("/" + LOCAL_TOKEN_ENDPOINT, response_model=Token)
    def post_login_for_local_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(OAuth2PasswordRequestForm),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        user_repo = repo_layer.users
        user = local_authenticate_request_user(
            form_data.username, form_data.password, user_repo
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        requested_scopes = form_data.scopes or user.allowed_scopes

        if is_admin_user(user):
            for scope in requested_scopes:
                if scope not in user.allowed_scopes:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Cannot authorize selected scopes",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

        access_token = encode_local_access_token(
            {
                "sub": user.username,
                "user": json.loads(JwtUser(**user.dict()).json()),
                "scopes": requested_scopes,
            },
            app_local_jwt_secret_key(app),
        )

        return {"access_token": access_token, "token_type": "bearer"}

    @router.post("/token-to-cookie", response_model=bool)
    def token_to_cookie(
        token: str = Depends(local_oauth2_scheme),
        response: fastapi.Response = fastapi.Response(None),
    ):
        response.set_cookie(key=local_oauth2_scheme.cookie_name, value=token)
        return True

    @router.post("/logout", response_model=bool)
    def logout(response: fastapi.Response = fastapi.Response(None)):
        response.delete_cookie(key=local_oauth2_scheme.cookie_name)
        return True

    @router.post(
        "/users/",
        response_model=models.SafeUser,
        status_code=fastapi.status.HTTP_201_CREATED,
    )
    def create(
        new_user: NewUser,
        current_user: ScopedUser = Security(request_user(app), scopes=[ADMIN_SCOPE]),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        new_user_dict = new_user.dict()
        new_user_dict["hashed_password"] = hash_password(new_user_dict["password"])
        del new_user_dict["password"]

        return repo_layer.users.create(models.User(**new_user_dict))

    @router.get("/users/me", response_model=ScopedUser)
    def me(current_user: ScopedUser = Security(request_user(app))):
        return current_user

    @router.get("/users/{id}", response_model=models.SafeUser)
    def read(
        id: str,
        current_user: ScopedUser = Security(request_user(app), scopes=[ADMIN_SCOPE]),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        result = repo_layer.users.query_one(id=id)
        if result is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return result

    @router.get("/users/", response_model=typing.List[models.SafeUser])
    def query(
        username: str = None,
        allowed_scopes: List[str] = None,
        local_claim_name: str = None,
        active: bool = fastapi.Query(True),
        current_user: ScopedUser = Security(request_user(app), scopes=[ADMIN_SCOPE]),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        return list(
            map(
                lambda u: models.SafeUser(**u.dict()),
                repo_layer.users.query(
                    username=username,
                    allowed_scopes=allowed_scopes,
                    local_claim_name=local_claim_name,
                    active=active,
                ),
            )
        )

    @router.patch("/users/{id}", response_model=bool)
    def patch(
        id: str,
        changes: List[endpoints.Change],
        current_user: models.User = Security(request_user(app), scopes=[ADMIN_SCOPE]),
        repo_layer=Depends(request_repo_layer(app)),
    ):
        def update_fn(metadata: models.User):

            for change in changes:
                if change.op == "replace":
                    setattr(metadata, change.path, change.value)
                elif change.op == "remove":
                    setattr(metadata, change.path, None)

            return metadata

        modified = repo_layer.users.partial_update(
            id,
            update_fn,
        )

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.delete("/users/{id}", response_model=bool)
    def delete(
        id: str,
        preserve_data: bool = True,
        current_user: models.User = Security(request_user(app), scopes=[ADMIN_SCOPE]),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        modified = (
            repo_layer.users.deactivate if preserve_data else repo_layer.users.delete
        )(id)

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.get("/scopes/", response_model=typing.Dict)
    def query_scopes(
        current_user: ScopedUser = Security(request_user(app)),
        repo_layer=Depends(request_repo_layer(app)),
    ):
        return SCOPES

    return router


def init_request_user(app: fastapi.FastAPI, get_request_user):
    app.state.security_request_user = get_request_user


def request_user(app: fastapi.FastAPI):
    return app.state.security_request_user


def reload_project_claims(app: fastapi.FastAPI):
    return request_user(app).reload_claims()


def init_app_local_jwt_secret_key(app: fastapi.FastAPI, local_jwt_secret_key):
    app.state.security_local_jwt_secret_key = local_jwt_secret_key


def app_local_jwt_secret_key(app: fastapi.FastAPI):
    return app.state.security_local_jwt_secret_key


#
# Utilities
#

password_context = passlib.context.CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password):
    return password_context.hash(password)


def verify_password(password, password_hash):
    return password_context.verify(password, password_hash)


def encode_local_access_token(
    data: dict,
    jwt_secret_key: str,
    expires_delta=timedelta(minutes=LOCAL_ACCESS_TOKEN_EXPIRE_MINUTES),
):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jose.jwt.encode(
        to_encode, jwt_secret_key, algorithm=LOCAL_JWT_ALGORITHM
    )
    return encoded_jwt


def decode_local_access_token(token_jwt: str, jwt_secret_key: str):
    return jose.jwt.decode(token_jwt, jwt_secret_key, algorithms=[LOCAL_JWT_ALGORITHM])


def encode_pagination_token(*args, **kwargs):
    return encode_local_access_token(*args, **kwargs)


def decode_pagination_token(*args, **kwargs):
    return decode_local_access_token(*args, **kwargs)
