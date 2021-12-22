from fastapi import Depends
from sqlmodel import Session

from . import storage
from . import models

ADMIN_SCOPE_NAME = "*"

SCOPES = {
    ADMIN_SCOPE_NAME: "Admin Scope"
}

def get_session():
    with Session(storage.engine) as session:
        yield session

def get_config_kv_repository(session: Session = Depends(get_session)):
    return models.ConfigKvRepository(session)

def get_user_repository(session: Session = Depends(get_session)):
    return models.UserRepository(session)