from typing import Optional
import pydantic
import bson

class PyObjectId(bson.ObjectId):

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not bson.ObjectId.is_valid(v):
            raise ValueError('Invalid objectid')
        return bson.ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type='string')
  

class ConfigKv(pydantic.BaseModel):
    key: Optional[PyObjectId] = pydantic.Field(alias='_id')
    value: Optional[str]

class User(pydantic.BaseModel):
    id: Optional[PyObjectId] = pydantic.Field(alias='_id')
    username: str
    hashed_password: str
    disabled: bool = False

# class Scope(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     name: str
#     description: str

import pymongo
import pymongo.collection
import pymongo.errors
import pymongo.database
import pymongo.client_session

class BaseRepository:

    def __init__(self, session: pymongo.client_session.ClientSession):

        self.session = session
        self.client: pymongo.MongoClient = session.client
        self.db: pymongo.database.Database = self.client.get_default_database()

class ConfigKvRepository(BaseRepository):

    """
    NOTE that the API here is intended to mimic a dict
    """

    def get(self, key, default_value=None):
        doc = self.db["config_kv"].find_one({ "_id": key })
        if doc is None: return default_value
        return doc["value"]

    def set(self, key, value):
        doc = { "_id": key, "value": value }
        self.db["config_kv"].replace_one({ "_id": key }, doc, upsert=True)

    def setdefault(self, key, default_value):
        doc = { "_id": key, "value": default_value }
        updated = self.db["config_kv"].find_one_and_update(
            { "_id": key },
            { "$setOnInsert": { "value": default_value } }, 
            upsert=True, return_document=pymongo.collection.ReturnDocument.AFTER)
        return updated["value"]

def undef_id(doc):
    doc = dict(doc)
    if doc["_id"] is None:
        del doc["_id"]
    return doc

class UserRepository(BaseRepository):

    def create_user(self, user: User):
        result = self.db["user"].insert_one(undef_id(user.dict(by_alias=True)))
        user.id = result.inserted_id
        return user

    def get_user_by_username(self, username: str):
        doc = self.db["user"].find_one({ "username": username })
        if doc is None: return None
        return User(**doc)

    def get_all_users(self):
        return map(lambda doc: User(**doc), list(self.db["user"].find()))

    # def create_scope(self, scope: Scope):
    #     self.session.add(scope)
    #     self.auto_commit()

    # def get_scope_by_name(self, name: str):
    #     return self.session.execute(select(Scope).where(Scope.name == name)).fetchone()

    # def get_all_scopes(self):
    #     return self.session.execute(select(Scope)).fetchall()

class RepositoryLayer:

    def __init__(self, session: pymongo.client_session.ClientSession):
        self.session = session

    def get(self, clazz):
        return clazz(self.session)
