from typing import Optional, List, ClassVar, Any, Union
import fastapi
import fastapi.encoders
import pydantic
import bson
import datetime

from mppw import logger

import pymongo
import pymongo.collection
import pymongo.errors
import pymongo.database
import pymongo.client_session

from . import models
from . import storage

def init_request_repo_layer(app: fastapi.FastAPI):

    storage_layer = storage.app_storage_layer(app)

    if isinstance(storage_layer, storage.MongoDBStorageLayer):

        def request_repo_layer():
            with storage_layer.start_session() as session:
                yield MongoDBRepositoryLayer(storage_layer, session)

        app.state.repositories_request_repo_layer = request_repo_layer

        def cb_repo_layer(cb):
            with storage_layer.start_session() as session:
                cb(MongoDBRepositoryLayer(storage_layer, session))

        app.state.repositories_cb_repo_layer = cb_repo_layer
    
    else:
        raise Exception(f"No repository layer matches storage layer of type {type(storage_layer)}")

def app_storage_layer(app: fastapi.FastAPI):
    return storage.app_storage_layer(app)

def request_repo_layer(app: fastapi.FastAPI):
    return app.state.repositories_request_repo_layer

def using_app_repo_layer(app: fastapi.FastAPI, cb):
    app.state.repositories_cb_repo_layer(cb)

#
# MongoDB repository layer implementation
#

class MongoDBRepositoryLayer:

    def __init__(self, storage_layer: storage.MongoDBStorageLayer, session: pymongo.client_session.ClientSession):
        
        self.storage_layer = storage_layer
        self.session = session

        self.kv = ConfigKvRepository(self.session)
        self.users = UserRepository(self.session)
        self.artifacts = ArtifactRepository(self.session)
        self.operations = OperationRepository(self.session)

class MongoDBRepository:

    def __init__(self, session: pymongo.client_session.ClientSession):

        self.session = session
        self.client: pymongo.MongoClient = session.client
        self.db: pymongo.database.Database = self.client.get_default_database()

class ConfigKvRepository(MongoDBRepository):

    """
    NOTE that the API here is intended to mimic a dict
    """

    @property
    def collection(self) -> pymongo.collection.Collection:
        return self.db["config_kv"]

    def get(self, key, default_value=None):
        doc = self.collection.find_one({ "_id": key })
        if doc is None: return default_value
        return doc["value"]

    def set(self, key, value):
        doc = { "_id": key, "value": value }
        self.collection.replace_one({ "_id": key }, doc, upsert=True)

    def setdefault(self, key, default_value):
        updated = self.collection.find_one_and_update(
            { "_id": key },
            { "$setOnInsert": { "value": default_value } }, 
            upsert=True, return_document=pymongo.collection.ReturnDocument.AFTER)
        return updated["value"]

def model_to_doc(model):
    if model is None: return None
    doc = model.dict()
    if "id" in doc:
        doc["_id"] = doc["id"]
        del doc["id"]
    if doc["_id"] is None:
        del doc["_id"]
    return doc

def doc_to_model(doc, clazz):
    if doc is None: return None
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = doc["_id"]
        del doc["_id"]
    return clazz(**doc)

class UserRepository(MongoDBRepository):

    @property
    def collection(self) -> pymongo.collection.Collection:
        return self.db["users"]

    def create(self, user: models.User):
        result = self.collection.insert_one(model_to_doc(user))
        user.id = result.inserted_id
        return user

    def query(self, username=None):
        if username is None:
            return map(lambda doc: doc_to_model(doc, models.User), list(self.collection.find()))
        else:
            return doc_to_model(self.collection.find_one({ "username": username }), models.User)

    # def create_scope(self, scope: Scope):
    #     self.session.add(scope)
    #     self.auto_commit()

    # def get_scope_by_name(self, name: str):
    #     return self.session.execute(select(Scope).where(Scope.name == name)).fetchone()

    # def get_all_scopes(self):
    #     return self.session.execute(select(Scope)).fetchall()


class UnknownArtifactTypeException(Exception):
    pass

class ArtifactRepository(MongoDBRepository):

    @staticmethod
    def doc_to_artifact(doc):
        if doc is None: return None
        elif doc["type_urn"].startswith(models.MaterialArtifact.URN_PREFIX):
            return doc_to_model(doc, models.MaterialArtifact)
        elif doc["type_urn"].startswith(models.DigitalArtifact.URN_PREFIX):
            return doc_to_model(doc, models.DigitalArtifact)
        else:
            raise UnknownArtifactTypeException()

    @property
    def collection(self) -> pymongo.collection.Collection:
        return self.db["artifacts"]

    def create(self, artifact: models.Artifact):
        result = self.collection.insert_one(model_to_doc(artifact))
        artifact.id = result.inserted_id
        return artifact

    def read(self, id: str):
        return type(self).doc_to_artifact(self.collection.find_one({ "_id": bson.ObjectId(id) }))

    def query(self):
        return map(lambda doc: type(self).doc_to_artifact(doc), list(self.collection.find()))

    def delete(self, id: str):
        return self.collection.delete_one({ "_id": bson.ObjectId(id) }).deleted_count
    

class OperationRepository(MongoDBRepository):

    @staticmethod
    def doc_to_artifact(doc):
        if doc is None:
            return None
        else:
            return doc_to_model(doc, models.Operation)

    @property
    def collection(self) -> pymongo.collection.Collection:
        return self.db["operations"]

    def create(self, operation: models.Operation):
        result = self.collection.insert_one(model_to_doc(operation))
        operation.id = result.inserted_id
        return operation

    def read(self, id: str):
        return type(self).doc_to_artifact(self.collection.find_one({ "_id": bson.ObjectId(id) }))

    def query(self):
        return map(lambda doc: type(self).doc_to_artifact(doc), list(self.collection.find()))

    def delete(self, id: str):
        return self.collection.delete_one({ "_id": bson.ObjectId(id) }).deleted_count
