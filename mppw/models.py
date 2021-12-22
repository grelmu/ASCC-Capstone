from typing import Optional
from sqlmodel import SQLModel, Field, Session, create_engine
from sqlalchemy import select, insert
import sqlmodel.main

# DRAGONS: We're limited to a single set of models in a single DB here -
# the metadata tracked by SQLModel can't be divided into separate
# models
registry = sqlmodel.main.default_registry

class ConfigKv(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str
    value: Optional[str]

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    hashed_password: str
    disabled: bool = False

# class Scope(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     name: str
#     description: str

class BaseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.use_auto_commit = True

    def auto_commit(self):
        if not self.use_auto_commit: return
        self.commit()

    def commit(self):
        self.session.commit()

class ConfigKvRepository(BaseRepository):

    def get(self, key, default_value=None):
        kv = self.session.execute(select(ConfigKv).where(ConfigKv.key == key)).one_or_none()
        return kv[0] if kv is not None else default_value

    def set(self, key, value):
        kv = ConfigKv(key=key, value=value)
        self.session.add(kv)
        self.auto_commit()
        return kv

    def setdefault(self, key, default_value):
        kv = self.session.execute(select(ConfigKv).where(ConfigKv.key == key)).one_or_none()
        if kv is None:
            kv = (self.set(key, default_value),)
        return kv[0]

class UserRepository(BaseRepository):

    def create_user(self, user: User):
        self.session.add(user)
        self.auto_commit()

    def get_user_by_username(self, username: str):
        user = self.session.execute(select(User).where(User.username == username)).one_or_none()
        return user[0] if user else None

    # def create_scope(self, scope: Scope):
    #     self.session.add(scope)
    #     self.auto_commit()

    # def get_scope_by_name(self, name: str):
    #     return self.session.execute(select(Scope).where(Scope.name == name)).fetchone()

    # def get_all_scopes(self):
    #     return self.session.execute(select(Scope)).fetchall()

class RepositoryLayer:

    def __init__(self, session: Session):
        self.session = session

    def get(self, clazz):
        return clazz(self.session)
