from gc import collect
import typing
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

mdb_codec_options = bson.codec_options.CodecOptions(type_registry=bson.codec_options.TypeRegistry([models.ObjectDbId.bson_encoder(), models.StrDbId.bson_encoder()]))

class MongoDBRepositoryLayer:

    def __init__(self, storage_layer: storage.MongoDBStorageLayer, session: pymongo.client_session.ClientSession):
        
        self.storage_layer = storage_layer
        self.session = session

        self.kv = ConfigKvRepository(self.session)
        self.users = UserRepository(self.session)
        self.projects = ProjectRepository(self.session)
        self.operations = OperationRepository(self.session)
        self.artifacts = ArtifactRepository(self.session)
        self.buckets = BucketRepository(self.storage_layer)

class MongoDBRepository:

    def __init__(self, session: pymongo.client_session.ClientSession):

        self.session = session
        self.client: pymongo.MongoClient = session.client
        self.db: pymongo.database.Database = self.client.get_default_database()

    def query_one(self, *args, **kwargs):
        return (list(self.query(*args, **kwargs)) or [None])[0]

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
    return models.DbId.validate(id)

def coerce_model_id(model):
    if model is None: return None
    return coerce_doc_id(model.id)

def model_to_doc(model):
    if model is None: return None
    doc = model.dict()
    if "id" in doc:
        doc["_id"] = doc["id"]
        del doc["id"]
    if "_id" in doc and doc["_id"] is None:
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
        return self.db.get_collection("users", codec_options=mdb_codec_options)

    def _query_doc_for(self, id: str = None, username: str = None, active: bool = None):
        query_doc = {}
        if id is not None: query_doc["_id"] = coerce_doc_id(id)
        if username is not None: query_doc["username"] = username
        if active is not None: query_doc["active"] = { "$ne": False } if active else False
        return query_doc

    def create(self, user: models.User):
        result = self.collection.insert_one(model_to_doc(user))
        user.id = models.ObjectDbId(result.inserted_id)
        return user

    def query(self, id=None, username=None, active=None):
        logger.warn(self._query_doc_for(id=id, username=username, active=active))
        return map(lambda doc: doc_to_model(doc, models.User), list(self.collection.find(
            self._query_doc_for(id=id, username=username, active=active))))

    def deactivate(self, id: str):
        return self.collection.update_one(
            self._query_doc_for(id=id), { "$set": { "active": False }}).modified_count == 1

    def delete(self, id: str):
        return self.collection.delete_one(self._query_doc_for(id=id)).deleted_count == 1

    # def create_scope(self, scope: Scope):
    #     self.session.add(scope)
    #     self.auto_commit()

    # def get_scope_by_name(self, name: str):
    #     return self.session.execute(select(Scope).where(Scope.name == name)).fetchone()

    # def get_all_scopes(self):
    #     return self.session.execute(select(Scope)).fetchall()


class ProjectRepository(MongoDBRepository):

    @property
    def collection(self) -> pymongo.collection.Collection:
        return self.db.get_collection("projects", codec_options=mdb_codec_options)

    def _query_doc_for(self, ids: List[str] = None, name: Optional[str] = None, active: Optional[bool] = None):
        query_doc = {}
        if ids is not None: query_doc["_id"] = { "$in": list(map(coerce_doc_id, ids)) }
        if name is not None: query_doc["name"] = name
        if active is not None: query_doc["active"] = { "$ne": False } if active else False
        return query_doc

    def create(self, project: models.Project):
        result = self.collection.insert_one(model_to_doc(project))
        project.id = models.ObjectDbId(result.inserted_id)
        return project

    def query(self, ids=None, name=None, active=None):
        return map(lambda doc: doc_to_model(doc, models.Project), list(self.collection.find(
            self._query_doc_for(ids=ids, name=name, active=active))))

    def deactivate(self, id: str):
        return self.collection.update_one(
            self._query_doc_for(ids=[id]), { "$set": { "active": False }}).modified_count == 1

    def delete(self, id: str):
        return self.collection.delete_one(self._query_doc_for(ids=[id])).deleted_count == 1

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
        return self.db.get_collection("artifacts", codec_options=mdb_codec_options)

    def _query_doc_for(self, id: str = None, project_ids: List[str] = None, active: Optional[bool] = None):
        query_doc = {}
        if id is not None: query_doc["_id"] = coerce_doc_id(id)
        if project_ids is not None: query_doc["project"] = { "$in": list(map(coerce_doc_id, project_ids)) }
        if active is not None: query_doc["active"] = { "$ne": False } if active else False
        return query_doc

    def create(self, artifact: models.Artifact):
        result = self.collection.insert_one(model_to_doc(artifact))
        artifact.id = models.ObjectDbId(result.inserted_id)
        return artifact

    def query(self, id: str = None, project_ids: List[str] = None, active: Optional[bool] = None):
        return map(lambda doc: type(self).doc_to_artifact(doc), list(self.collection.find(
            self._query_doc_for(id=id, project_ids=project_ids, active=active))))
        
    def update(self, artifact: models.Artifact, project_ids: List[str] = None):
        return self.collection.replace_one(
            self._query_doc_for(id=artifact.id, project_ids=project_ids), model_to_doc(artifact)).modified_count == 1

    def deactivate(self, id: str, project_ids: List[str] = None):
        return self.collection.update_one(
            self._query_doc_for(id=id, project_ids=project_ids), { "$set": { "active": False }}).modified_count == 1

    def delete(self, id: str, project_ids: List[str] = None):
        return self.collection.delete_one(
            self._query_doc_for(id=id, project_ids=project_ids)).deleted_count == 1
    

class OperationRepository(MongoDBRepository):

    @property
    def collection(self) -> pymongo.collection.Collection:
        return self.db.get_collection("operations", codec_options=mdb_codec_options)

    def _query_doc_for(self, id: str = None, project_ids: List[str] = None, name: Optional[str] = None, active: Optional[bool] = None):
        query_doc = {}
        if id is not None: query_doc["_id"] = coerce_doc_id(id)
        if project_ids is not None: query_doc["project"] = { "$in": list(map(coerce_doc_id, project_ids)) }
        if name is not None: query_doc["name"] = name
        if active is not None: query_doc["active"] = { "$ne": False } if active else False
        return query_doc

    def create(self, operation: models.Operation):
        result = self.collection.insert_one(model_to_doc(operation))
        operation.id = models.ObjectDbId(result.inserted_id)
        return operation

    def query(self, id: str = None, project_ids: List[str] = None, name: Optional[str] = None, active: Optional[bool] = None):
        return map(lambda doc: doc_to_model(doc, models.Operation), list(self.collection.find(
            self._query_doc_for(id=id, project_ids=project_ids, name=name, active=active))))

    def attach(self, id: str, transform: models.ArtifactTransform, project_ids: List[str] = None):
        return self.collection.update_one(
            self._query_doc_for(id=id, project_ids=project_ids), { "$push" : { "artifact_transform_graph": model_to_doc(transform) }}).modified_count == 1

    def detach(self, id: str, kind_urn: str, project_ids: List[str] = None):
        return self.collection.update_one(
            self._query_doc_for(id=id, project_ids=project_ids), { "$pull" : { "artifact_transform_graph": { "kind_urn": kind_urn }}}).modified_count == 1

    def deactivate(self, id: str, project_ids: List[str] = None):
        return self.collection.update_one(
            self._query_doc_for(id=id, project_ids=project_ids), { "$set": { "active": False }}).modified_count == 1

    def delete(self, id: str, project_ids: List[str] = None):
        return self.collection.delete_one(
            self._query_doc_for(id=id, project_ids=project_ids)).deleted_count == 1

class UnsupportedSchemeException(Exception):
    pass

class UnmanagedBucketException(Exception):
    pass

class BucketRepository:

    MONGODB_SCHEME = "mongodb"
    GRIDFS_SCHEME = "mongodb+gridfs"

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

    def create_local_mdb_user(self, username, db_name, coll_names=None, read_only=False, password=None):

        password = password if password is not None else secrets.token_hex(32)
        role_name = f"{username}-role"

        db = self.storage_layer.mdb_client[db_name]

        role_doc = None
        if coll_names is None:

            roles = None
            if not read_only:
                roles = [{ "role": "dbAdmin", "db": db_name }, { "role": "readWrite", "db": db_name }]
            else:
                roles = [{ "role": "read", "db": db_name }]

            role_doc = {
                "createRole": role_name,
                "privileges": [],
                "roles": roles
            }

        else:
            
            priv_docs = []
            for coll_name in coll_names:

                if not read_only:
                    priv_docs.append({
                        "resource": { "db": db_name, "collection": coll_name },
                        "actions": ["find", "insert", "update", "remove", "changeStream",
                                    "listIndexes", "createIndex", "reIndex", "dropIndex",
                                    "collStats", "indexStats"]
                    })
                else:
                    priv_docs.append({
                        "resource": { "db": db_name, "collection": coll_name },
                        "actions": ["find", "changeStream", "listIndexes", "collStats", "indexStats"]
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
        
        db_furl = furl.furl(f"{mdb_furl.scheme}://{self.storage_layer.local_storage_url_host()}/{db_name}")
        return db_furl

    def create_local_mdb_bucket(self, bucket_id):

        suffixes = ["bucket", bucket_id]
        bucket_furl = self.create_local_mdb_furl(db_suffix="-".join(suffixes))
        bucket_furl.username, bucket_furl.password = self.create_local_mdb_user(f"bucket-{bucket_id}-user", bucket_furl.path.segments[0])
        self.create_local_mdb_user(f"{bucket_furl.username}-ro", bucket_furl.path.segments[0], read_only=True, password=bucket_furl.password[0:int(len(bucket_furl.password) / 2)])

        return bucket_furl.url

    def drop_local_mdb_bucket(self, bucket_url):
        
        bucket_furl = furl.furl(bucket_url)
        db_name = bucket_furl.path.segments[0]

        self.drop_local_mdb_user(bucket_furl.username, db_name)
        try:
            self.drop_local_mdb_user(f"{bucket_furl.username}-ro", db_name)
        except Exception as ex:
            logger.warn(f"Could not drop read-only user for {bucket_furl.username}:\n{ex}")

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
        self.create_local_mdb_user(f"{bucket_furl.username}-ro", bucket_furl.path.segments[0], read_only=True, password=bucket_furl.password[0:int(len(bucket_furl.password) / 2)])

        return bucket_furl.url

    def drop_local_gridfs_bucket(self, bucket_url):

        bucket_furl = furl.furl(bucket_url)
        db_name = bucket_furl.path.segments[0]
        bucket_id = bucket_furl.path.segments[1]

        self.drop_local_mdb_user(bucket_furl.username, db_name)
        try:
            self.drop_local_mdb_user(f"{bucket_furl.username}-ro", db_name)
        except Exception as ex:
            logger.warn(f"Could not drop read-only user for {bucket_furl.username}:\n{ex}")

        db = self.storage_layer.mdb_client[db_name]
        bucket = gridfs.GridFSBucket(db, bucket_id)
        
        db.drop_collection(bucket._files)
        db.drop_collection(bucket._chunks)

    def delete_mdb_bucket(self, bucket_furl):

        if bucket_furl.host == self.storage_layer.local_storage_url_host():
            return self.drop_local_mdb_bucket(bucket_furl.url)
        else:
            raise UnmanagedBucketException(bucket_furl.url)

    def delete_gridfs_bucket(self, bucket_furl):

        if bucket_furl.host == self.storage_layer.local_storage_url_host():
            return self.drop_local_gridfs_bucket(bucket_furl.url)
        else:
            raise UnmanagedBucketException(bucket_furl.url)






