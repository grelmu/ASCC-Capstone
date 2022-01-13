from gc import collect
from typing import Optional, List, ClassVar, Any, Union
import fastapi
import fastapi.encoders
import pydantic
import bson
import datetime
import furl
import secrets

from mppw import logger

import pymongo
import pymongo.collection
import pymongo.errors
import pymongo.database
import pymongo.client_session
import gridfs

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
        self.buckets = BucketRepository(self.storage_layer)

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

def coerce_doc_id(id):
    if id is None: return None
    try:
        return bson.ObjectId(id)
    except:
        return id

def coerce_model_id(model):
    if model is None: return None
    return coerce_doc_id(model.id)

def model_to_doc(model):
    if model is None: return None
    doc = model.dict()
    if "id" in doc:
        doc["_id"] = doc["id"]
        del doc["id"]
    
    if doc["_id"] is None:
        del doc["_id"]
    else:
        doc["_id"] = coerce_doc_id(doc["_id"])

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
        return type(self).doc_to_artifact(self.collection.find_one({ "_id": coerce_doc_id(id) }))

    def query(self):
        return map(lambda doc: type(self).doc_to_artifact(doc), list(self.collection.find()))

    def update(self, artifact: models.Artifact):
        logger.warn(model_to_doc(artifact))
        return self.collection.replace_one({ "_id": coerce_model_id(artifact) }, model_to_doc(artifact)).modified_count

    def delete(self, id:str ):
        return self.collection.delete_one({ "_id": coerce_doc_id(id) }).deleted_count
    

class OperationRepository(MongoDBRepository):

    @property
    def collection(self) -> pymongo.collection.Collection:
        return self.db["operations"]

    def create(self, operation: models.Operation):
        result = self.collection.insert_one(model_to_doc(operation))
        operation.id = result.inserted_id
        return operation

    def read(self, id: str):
        return type(self).doc_to_artifact(self.collection.find_one({ "_id": coerce_doc_id(id) }))

    def query(self):
        return map(lambda doc: doc_to_model(doc, models.Operation), list(self.collection.find()))

    def delete(self, id: str):
        return self.collection.delete_one({ "_id": coerce_doc_id(id) }).deleted_count

class UnsupportedSchemeException(Exception):
    pass

class UnmanagedBucketException(Exception):
    pass

class BucketRepository:

    MONGODB_SCHEME = "mongodb"
    GRIDFS_SCHEME = "mongodb+gridfs"

    LOCAL_MONGODB_HOST = "mongodb.mppw.local"

    def __init__(self, storage_layer: storage.MongoDBStorageLayer):
        self.storage_layer = storage_layer

    @property
    def default_db_bucket_scheme(self):
        return BucketRepository.MONGODB_SCHEME

    @property
    def default_file_bucket_scheme(self):
        return BucketRepository.GRIDFS_SCHEME

    def create_db_bucket(self, bucket_id, bucket_scheme):

        if bucket_scheme == BucketRepository.MONGODB_SCHEME:
            return self.create_local_mdb_bucket(bucket_id)
        else:
            raise UnsupportedSchemeException(bucket_scheme)

    def create_file_bucket(self, bucket_id, bucket_scheme):

        if bucket_scheme == BucketRepository.GRIDFS_SCHEME:
            return self.create_local_gridfs_bucket(bucket_id)
        else:
            raise UnsupportedSchemeException(bucket_scheme)

    def delete_bucket(self, bucket_url):

        bucket_furl = furl.furl(bucket_url)
        if bucket_furl.scheme in [BucketRepository.MONGODB_SCHEME]:
            return self.delete_mdb_bucket(bucket_furl)
        elif bucket_furl.scheme in [BucketRepository.GRIDFS_SCHEME]:
            return self.delete_gridfs_bucket(bucket_furl)
        else:
            raise UnsupportedSchemeException(bucket_furl.url)

    #
    # Local MongoDB specific implementation below
    #

    def create_local_mdb_user(self, username, db_name, coll_names=None):

        password = secrets.token_hex(32)
        role_name = f"{username}-role"

        db = self.storage_layer.mdb_client[db_name]

        role_doc = None
        if coll_names is None:
            role_doc = {
                "createRole": role_name,
                "privileges": [],
                "roles": [{ "role": "dbAdmin", "db": db_name }, { "role": "readWrite", "db": db_name }]
            }

        else:
            
            priv_docs = []
            for coll_name in coll_names:
                priv_docs.append({
                    "resource": { "db": db_name, "collection": coll_name },
                    "actions": ["find", "insert", "update", "remove", "changeStream",
                                "listIndexes", "createIndex", "reIndex", "dropIndex",
                                "collStats", "indexStats"]
                })

            role_doc = {
                "createRole": role_name,
                "privileges": priv_docs,
                "roles": []
            }

        user_doc = {
            "createUser": username,
            "pwd": password,
            "customData": { 
                "auto": True,
                "created": datetime.datetime.now().isoformat()
            },
            "roles": [{ "role": role_name, "db": db_name }]
        }

        db.command(role_doc)
        db.command(user_doc)

        return (username, password)

    def drop_local_mdb_user(self, username, db_name):

        role_name = f"{username}-role"

        db = self.storage_layer.mdb_client[db_name]

        db.command("dropUser", username)
        try:
            db.command("dropRole", role_name)
        except Exception as ex:
            logger.warn(f"Could not drop role {role_name} for {username}:\n{ex}")

    def create_local_mdb_furl(self, db_suffix=None):
        
        mdb_furl = furl.furl(self.storage_layer.mdb_url)
        default_db_name = self.storage_layer.mdb_client.get_default_database().name

        db_names = [default_db_name]
        if db_suffix: db_names.append(db_suffix)
        db_name = "-".join(db_names)
        
        db_furl = furl.furl(f"{mdb_furl.scheme}://{BucketRepository.LOCAL_MONGODB_HOST}/{db_name}")
        return db_furl

    def create_local_mdb_bucket(self, bucket_id):

        suffixes = ["bucket", bucket_id]
        bucket_furl = self.create_local_mdb_furl(db_suffix="-".join(suffixes))
        bucket_furl.username, bucket_furl.password = self.create_local_mdb_user(f"bucket-{bucket_id}-user", bucket_furl.path.segments[0])
        return bucket_furl.url

    def drop_local_mdb_bucket(self, bucket_url):
        
        bucket_furl = furl.furl(bucket_url)
        db_name = bucket_furl.path.segments[0]

        self.drop_local_mdb_user(bucket_furl.username, db_name)
        self.storage_layer.mdb_client.drop_database(db_name)

    def create_local_gridfs_bucket(self, bucket_id):

        bucket_furl = self.create_local_mdb_furl(db_suffix="gridfs")
        bucket_furl.scheme = BucketRepository.GRIDFS_SCHEME
        bucket_furl.path.add(bucket_id)

        db_name = bucket_furl.path.segments[0]
        db = self.storage_layer.mdb_client[db_name]

        bucket = gridfs.GridFSBucket(db, bucket_id)
        coll_names = [coll.name for coll in [bucket._files, bucket._chunks]]

        bucket_furl.username, bucket_furl.password = \
            self.create_local_mdb_user(f"gridfs-{bucket_id}-user", bucket_furl.path.segments[0], coll_names=coll_names)

        return bucket_furl.url

    def drop_local_gridfs_bucket(self, bucket_url):

        bucket_furl = furl.furl(bucket_url)
        db_name = bucket_furl.path.segments[0]
        bucket_id = bucket_furl.path.segments[1]

        self.drop_local_mdb_user(bucket_furl.username, db_name)

        db = self.storage_layer.mdb_client[db_name]
        bucket = gridfs.GridFSBucket(db, bucket_id)
        
        db.drop_collection(bucket._files)
        db.drop_collection(bucket._chunks)

    def delete_mdb_bucket(self, bucket_furl):

        if bucket_furl.host == BucketRepository.LOCAL_MONGODB_HOST:
            return self.drop_local_mdb_bucket(bucket_furl.url)
        else:
            raise UnmanagedBucketException(bucket_furl.url)

    def delete_gridfs_bucket(self, bucket_furl):

        if bucket_furl.host == BucketRepository.LOCAL_MONGODB_HOST:
            return self.drop_local_gridfs_bucket(bucket_furl.url)
        else:
            raise UnmanagedBucketException(bucket_furl.url)






