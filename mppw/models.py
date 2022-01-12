from typing import Optional, List, ClassVar, Any
import fastapi
import fastapi.encoders
import pydantic
import bson
import datetime

from mppw import logger

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

class DocModel(pydantic.BaseModel):

    id: Optional[PyObjectId] = pydantic.Field(alias='_id')

    class Config(pydantic.BaseConfig):
        json_encoders = {
            datetime.datetime: lambda dt: dt.isoformat(),
            bson.ObjectId: lambda oid: str(oid),
        }

class User(DocModel):
    username: str
    hashed_password: str
    disabled: bool = False

# class Scope(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     name: str
#     description: str

class GeometryLabel(pydantic.BaseModel):
    name: str
    coordinate: List[float]

class Artifact(DocModel):

    URN_PREFIX: ClassVar = "urn:x-mfg:artifact"

    type_urn: str
    name: Optional[str]
    description: Optional[str]
    tags: List[str]

class MaterialArtifact(Artifact):

    URN_PREFIX: ClassVar = f"{Artifact.URN_PREFIX}:material"

    material_system_urn: Optional[str]

    label: str
    geometry_labels: List[GeometryLabel]
    location_label: Optional[str]

    @pydantic.validator("type_urn")
    def valid_type_urn_prefix(cls, v):
        if not v.startswith(MaterialArtifact.URN_PREFIX):
            raise ValueError(f"material artifact URNs must start with {MaterialArtifact.URN_PREFIX}")
        return v

class DigitalArtifact(Artifact):

    URN_PREFIX: ClassVar = f"{Artifact.URN_PREFIX}:digital"

    local_data: Any
    url_data: Optional[str]

    @pydantic.validator("type_urn")
    def valid_type_urn_prefix(cls, v):
        if not v.startswith(DigitalArtifact.URN_PREFIX):
            raise ValueError(f"digital artifact URNs must start with {DigitalArtifact.URN_PREFIX}")
        return v

class ArtifactTransform(pydantic.BaseModel):

    URN_PREFIX: ClassVar = "urn:x-mfg:transform"

    kind_urn: str
    input_artifacts: List[PyObjectId]
    output_artifacts: List[PyObjectId]
    parameters: Any
    
class Operation(DocModel):

    URN_PREFIX: ClassVar = "urn:x-mfg:operation"

    type_urn: str
    name: Optional[str]
    description: Optional[str]
    tags: List[str]

    system_name: Optional[str]
    system_id: Optional[PyObjectId]
    human_operator_names: List[str]
    human_operator_ids: List[PyObjectId]

    start_at: Optional[datetime.datetime]
    end_at: Optional[datetime.datetime]
    status: Optional[str]

    artifact_transform_graph: List[ArtifactTransform]

    @pydantic.validator("type_urn")
    def valid_type_urn_prefix(cls, v):
        if not v.startswith(MaterialArtifact.URN_PREFIX):
            raise ValueError(f"operation URNs must start with {Operation.URN_PREFIX}")
        return v


import pymongo
import pymongo.collection
import pymongo.errors
import pymongo.database
import pymongo.client_session

from . import storage

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

    def query_users(self):
        return map(lambda doc: User(**doc), list(self.db["user"].find()))

    # def create_scope(self, scope: Scope):
    #     self.session.add(scope)
    #     self.auto_commit()

    # def get_scope_by_name(self, name: str):
    #     return self.session.execute(select(Scope).where(Scope.name == name)).fetchone()

    # def get_all_scopes(self):
    #     return self.session.execute(select(Scope)).fetchall()


class UnknownArtifactTypeException(Exception):
    pass

class ArtifactRepository(BaseRepository):

    @staticmethod
    def doc_to_artifact(doc):
        if doc is None:
            return None
        elif doc["type_urn"].startswith(MaterialArtifact.URN_PREFIX):
            return MaterialArtifact(**doc)
        elif doc["type_urn"].startswith(DigitalArtifact.URN_PREFIX):
            return DigitalArtifact(**doc)
        else:
            raise UnknownArtifactTypeException()

    @property
    def collection(self) -> pymongo.collection.Collection:
        return self.db["artifacts"]

    def create(self, artifact: Artifact):
        result = self.collection.insert_one(undef_id(artifact.dict(by_alias=True)))
        artifact.id = result.inserted_id
        return artifact

    def read(self, id: str):
        return type(self).doc_to_artifact(self.collection.find_one({ "_id": bson.ObjectId(id) }))

    def query(self):
        return map(lambda doc: type(self).doc_to_artifact(doc), list(self.collection.find()))

    def delete(self, id: str):
        return self.collection.delete_one({ "_id": bson.ObjectId(id) }).deleted_count
    

class OperationRepository(BaseRepository):

    @staticmethod
    def doc_to_artifact(doc):
        if doc is None:
            return None
        else:
            return Operation(**doc)

    @property
    def collection(self) -> pymongo.collection.Collection:
        return self.db["operations"]

    def create(self, operation: Operation):
        result = self.collection.insert_one(undef_id(operation.dict(by_alias=True)))
        operation.id = result.inserted_id
        return operation

    def read(self, id: str):
        return type(self).doc_to_artifact(self.collection.find_one({ "_id": bson.ObjectId(id) }))

    def query(self):
        return map(lambda doc: type(self).doc_to_artifact(doc), list(self.collection.find()))

    def delete(self, id: str):
        return self.collection.delete_one({ "_id": bson.ObjectId(id) }).deleted_count

class RepositoryLayer:

    def __init__(self, session: pymongo.client_session.ClientSession):
        self.session = session

    def get(self, clazz):
        return clazz(self.session)

def init_request_repo_layer(app: fastapi.FastAPI):

    model_storage_layer = storage.app_model_storage_layer(app)

    def request_repo_layer():
        with model_storage_layer.start_session() as session:
            yield RepositoryLayer(session)

    app.state.models_request_repo_layer = request_repo_layer

def request_repo_layer(app: fastapi.FastAPI) -> RepositoryLayer:
    return app.state.models_request_repo_layer