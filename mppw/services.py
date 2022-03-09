from typing import Optional, List, ClassVar, Any
import fastapi
from fastapi import Depends
import fastapi.encoders
import pydantic
import bson
import datetime
import bson
import furl

from mppw import logger

from . import models
from . import repositories

DATABASE_BUCKET_URN_PREFIX = f"{models.DigitalArtifact.URN_PREFIX}:database-bucket"
FILE_BUCKET_URN_PREFIX = f"{models.DigitalArtifact.URN_PREFIX}:file-bucket"

class AttachmentKind(pydantic.BaseModel):
    kind_urn: str
    artifact_type_urns: List[str]

    @staticmethod
    def make(kind_urn, artifact_type_urns):
        return AttachmentKind(kind_urn=kind_urn, artifact_type_urns=artifact_type_urns)

    @staticmethod
    def make_all(lst):
        return [AttachmentKind.make(*item) for item in lst]

class OperationServices:

    STATUS_DRAFT = "draft"

    ATTACHMENT_KINDS = AttachmentKind.make_all([
        (":process-data", [":digital:database-bucket", ":digital:file-bucket", ":digital:file"]),
        (":attachments", [":digital:file-bucket", ":digital:file"]),
    ])

    ARTIFACT_KIND_ATTACHMENTS = ":attachments"
    ARTIFACT_KIND_PROCESS_DATA = ":process-data"

    def __init__(self, repo_layer):
        self.repo_layer = repo_layer

    def set_default_fields(self, operation: models.Operation, clazz):

        if not operation.name:
            operation.name = clazz.DEFAULT_NAME

        if not operation.description:
            operation.description = clazz.DEFAULT_DESCRIPTION

        if operation.start_at is None:
            start_at = datetime.datetime.now()

        if not operation.status:
            operation.status = OperationServices.STATUS_DRAFT

    def create_default_attachments(self, project, scheme=None):

        attachments = models.DigitalArtifact(
            type_urn = FILE_BUCKET_URN_PREFIX,
            project = project,
            name = "Attachments",
            description = "Default attachments",
        )

        self.repo_layer.artifacts.create(attachments)
        self.initialize_file_bucket_artifact(attachments, scheme)
        self.repo_layer.artifacts.update(attachments)

        return models.ArtifactTransform(
            kind_urn = OperationServices.ARTIFACT_KIND_ATTACHMENTS,
            output_artifacts = [attachments.id]
        )

    def create_default_process_data(self, project, scheme=None):

        process_data = models.DigitalArtifact(
            type_urn = DATABASE_BUCKET_URN_PREFIX,
            project = project,
            name = "Process Data",
            description = "Default process data",   
        )

        self.repo_layer.artifacts.create(process_data)
        self.initialize_db_bucket_artifact(process_data, scheme)
        self.repo_layer.artifacts.update(process_data)

        return models.ArtifactTransform(
            kind_urn = OperationServices.ARTIFACT_KIND_PROCESS_DATA,
            output_artifacts = [process_data.id]
        )

    def initialize_artifact(self, id: str, scheme=None):
        artifact = self.repo_layer.artifacts.read(id)
        if artifact.type_urn.startswith(DATABASE_BUCKET_URN_PREFIX):
            return self.initialize_db_bucket_artifact(artifact)
        elif artifact.type_urn.startswith(FILE_BUCKET_URN_PREFIX):
            return self.initialize_file_bucket_artifact(artifact)
        else:
            return False

    def initialize_db_bucket_artifact(self, artifact: models.DigitalArtifact, scheme=None):

        bucket_id = f"artdb-{str(artifact.id)}"
        scheme = scheme or self.repo_layer.buckets.default_db_bucket_scheme
        artifact.url_data = self.repo_layer.buckets.create_db_bucket(bucket_id, scheme)
        return True

    def initialize_file_bucket_artifact(self, artifact: models.DigitalArtifact, scheme=None):

        bucket_id = f"artfiles-{str(artifact.id)}"
        scheme = scheme or self.repo_layer.buckets.default_file_bucket_scheme
        artifact.url_data = self.repo_layer.buckets.create_file_bucket(bucket_id, scheme)
        return True

    def get_transforms_of_kind(self, operation: models.Operation, kind_urn: str):

        transforms = []
        for transform in (operation.artifact_transform_graph or []):
            if transform.kind_urn == kind_urn or transform.kind_urn.startswith(kind_urn + ":"):
                transforms.append(transform)
        
        return transforms

    def get_transform_of_kind(self, operation: models.Operation, kind_urn: str):
        return (self.get_transforms_of_kind(operation, kind_urn) or [None])[0]

    def get_artifact_ids_of_kind(self, operation: models.Operation, kind_urn: str):

        artifact_ids = []
        for transform in self.get_transforms_of_kind(operation, kind_urn):
            artifact_ids.append(transform.output_artifacts[0])

        return artifact_ids

    def get_artifact_id_of_kind(self, operation: models.Operation, kind_urn: str):
        return (self.get_artifact_ids_of_kind(operation, kind_urn) or [None])[0]

    def get_artifact_of_kind(self, operation: models.Operation, kind_urn: str):
        artifact_id = self.get_artifact_id_of_kind(operation, kind_urn)
        if artifact_id is None: return None
        return self.repo_layer.artifacts.query_one(id=artifact_id)

    def get_default_attachments_artifact(self, operation: models.Operation):
        return self.get_artifact_of_kind(operation, OperationServices.ARTIFACT_KIND_ATTACHMENTS)

    def detach_artifacts(self, operation: models.Operation, kind_urn: str, artifact_ids):
        for transform in self.get_transforms_of_kind(operation, kind_urn):
            transform.input_artifacts = filter(lambda id: id not in artifact_ids, transform.input_artifacts)
            transform.output_artifacts = filter(lambda id: id not in artifact_ids, transform.output_artifacts)

class FffServices(OperationServices):

    URN_PREFIX = f"{models.Operation.URN_PREFIX}:fff"
    DEFAULT_NAME = "FFF Manufacture"
    DEFAULT_DESCRIPTION = "FFF or FDM manufacturing operation"

    ATTACHMENT_KINDS = AttachmentKind.make_all([
        (":input:toolpath", [":digital:toolpath"]),
        (":input:batch", [":material:batch"]),
        (":output:part", [":material:part"]),
        (":operator-notes", [":digital:markdown", ":digital:file"]),
    ])

    ARTIFACT_KIND_OPERATOR_NOTES = ":operator-notes"
    ARTIFACT_KIND_OUTPUT_PARTS = ":output-parts"

    def __init__(self, repo_layer):
        self.repo_layer = repo_layer
    
    def create_default(self, operation: models.Operation):

        self.set_default_fields(operation, type(self))
        
        if not operation.artifact_transform_graph:
            operation.artifact_transform_graph = [
                models.ArtifactTransform(
                    kind_urn=FffServices.ARTIFACT_KIND_OPERATOR_NOTES,
                ),
                models.ArtifactTransform(
                    kind_urn=FffServices.ARTIFACT_KIND_OUTPUT_PARTS,
                ),
                self.create_default_process_data(operation.project),
                self.create_default_attachments(operation.project),
            ]

        return self.repo_layer.operations.create(operation)

    @property
    def attachment_kinds(self):
        return FffServices.ATTACHMENT_KINDS + OperationServices.ATTACHMENT_KINDS

class ArtifactServices:

    def __init__(self, repo_layer):
        self.repo_layer = repo_layer


class FileServices(ArtifactServices):

    URN_PREFIX = f"{models.DigitalArtifact.URN_PREFIX}:file"

    def can_download(self, artifact: models.DigitalArtifact):
        file_furl = furl.furl(artifact.url_data)
        return file_furl.scheme in self.repo_layer.buckets.allowed_file_bucket_schemes

    def download(self, artifact: models.DigitalArtifact):
        return self.repo_layer.buckets.get_file_by_url(artifact.url_data)


class DatabaseBucketServices(ArtifactServices):

    URN_PREFIX = DATABASE_BUCKET_URN_PREFIX

    def init(self, artifact: models.DigitalArtifact, scheme=None):

        bucket_id = f"artdb-{str(artifact.id)}"
        scheme = scheme or self.repo_layer.buckets.default_db_bucket_scheme
        artifact.url_data = self.repo_layer.buckets.create_db_bucket(bucket_id, scheme)

        return self.repo_layer.artifacts.update(artifact)

class FileBucketServices(ArtifactServices):

    URN_PREFIX = FILE_BUCKET_URN_PREFIX

    def init(self, artifact: models.DigitalArtifact, scheme=None):

        bucket_id = f"artfiles-{str(artifact.id)}"
        scheme = scheme or self.repo_layer.buckets.default_file_bucket_scheme
        artifact.url_data = self.repo_layer.buckets.create_file_bucket(bucket_id, scheme)

        return self.repo_layer.artifacts.update(artifact)

    def upload(self, artifact: models.DigitalArtifact, path: str, file):
        return self.repo_layer.buckets.add_file_to_bucket(artifact.url_data, path, file)

    def download(self, artifact: models.DigitalArtifact, path: str):
        return self.repo_layer.buckets.get_file_by_path(artifact.url_data, path)

    def ls(self, artifact: models.DigitalArtifact, path: str):
        return self.repo_layer.buckets.ls_bucket(artifact.url_data, path)

    def rename(self, artifact: models.DigitalArtifact, path: str, new_path: str):
        return self.repo_layer.buckets.rename_file(artifact.url_data, path, new_path)
    
    def delete(self, artifact: models.DigitalArtifact, path: str):
        return self.repo_layer.buckets.delete_file_by_path(artifact.url_data, path)


class UnknownPointCloudTypeException(Exception):
    pass

class UnknownPointCloudStorageStrategyException(Exception):
    pass

class XyztPoint(models.BaseJsonModel):
    p: List
    ctx: Optional[Any]

class PointCloudServices(ArtifactServices):

    URN_PREFIX = f"{models.DigitalArtifact.URN_PREFIX}:point-cloud"

    def sample(self, cloud_artifact: models.DigitalArtifact, space_bounds, time_bounds):

        if not cloud_artifact.url_data:
            raise UnknownPointCloudTypeException("No URL found for point cloud.")
        
        cloud_furl = furl.furl(cloud_artifact.url_data)
        if cloud_furl.scheme == "mongodb+dbvox":
            return self.sample_mongodb_dbvox(cloud_furl.url, space_bounds, time_bounds)
        else:
            raise UnknownPointCloudTypeException(f"Unknown point cloud type for {cloud_furl.url}")

    class DbVoxMeta(pydantic.BaseModel):
        max_scale: int
        base_units: Optional[str]
        address_field: Optional[str] = "vaddr"
        dt_field: Optional[str] = "stamp"
        storage_strategy: str
        storage_strategy_params: Any

    class XyzFieldsParams(pydantic.BaseModel):
        x_field: str = "x"
        y_field: str = "y"
        z_field: str = "z"

    @staticmethod
    def in_space_bounds(xyz, space_bounds):
        return space_bounds[0][0] <= xyz[0] and xyz[0] < space_bounds[1][0] and \
               space_bounds[0][1] <= xyz[1] and xyz[1] < space_bounds[1][1] and \
               space_bounds[0][2] <= xyz[2] and xyz[2] < space_bounds[1][2]

    @staticmethod
    def in_spacetime_bounds(xyzt, space_bounds, time_bounds):
        return PointCloudServices.in_space_bounds(xyzt, space_bounds) and \
               (time_bounds is None or (
                   time_bounds[0] <= xyzt[3] and xyzt[3] < time_bounds[1]
               ))
    
    @staticmethod
    def mdb_vox_time_query(voxel, vaddr_field, time_bounds, dt_field):
        query = { vaddr_field: { "$regex" : "^" + voxel.to_addr() } }
        if time_bounds is not None:
            query[dt_field] = { "$gte" : time_bounds[0], "$lt": time_bounds[1] }
        return query

    def sample_mongodb_dbvox(self, dbvox_url, space_bounds, time_bounds):

        import pymongo
        import dbvox

        dbvox_furl = furl.furl(dbvox_url)
        base_furl = furl.furl(dbvox_furl)
        base_furl.scheme = "mongodb"
        base_furl.path = base_furl.path.segments[0]

        base_url = self.repo_layer.storage_layer.resolve_local_storage_url_host(base_furl.url)

        client = pymongo.MongoClient(base_url)
        collection = client[dbvox_furl.path.segments[0]][dbvox_furl.path.segments[1]]

        meta = PointCloudServices.DbVoxMeta(**(collection.find_one({ "_id": None })))
        space = dbvox.Vox3Space(meta.max_scale)
        voxels = space.get_cover(*(tuple(zip(*space_bounds))))

        vox_query = { "$or": [PointCloudServices.mdb_vox_time_query(voxel, meta.address_field, time_bounds, meta.dt_field) for voxel in voxels] }

        cursor = collection.find(vox_query)

        if meta.storage_strategy == "xyz_fields":
            params = PointCloudServices.XyzFieldsParams(**(meta.storage_strategy_params or {}))
            for doc in cursor:
                xyzt = [doc[params.x_field], doc[params.y_field], doc[params.z_field], doc[meta.dt_field]]
                if PointCloudServices.in_space_bounds(xyzt, space_bounds):
                    yield XyztPoint(p=xyzt, ctx=doc)

        else:
            raise UnknownPointCloudStorageStrategyException(f"Unknown storage strategy {meta.storage_strategy} for point cloud {dbvox_url}")


class ServicedOperationType(pydantic.BaseModel):
    urn_prefix: str
    name: str
    description: Optional[str]

class UnservicedOperationTypeException(Exception):
    pass

class UnservicedArtifactTypeException(Exception):
    pass

class ServiceLayer:

    ARTIFACT_SERVICE_TYPES = [FileServices, DatabaseBucketServices, FileBucketServices, PointCloudServices]
    OPERATION_SERVICE_TYPES = [FffServices]

    def __init__(self, repo_layer):
        self.repo_layer = repo_layer

    @property
    def operation_service_types(self):
        return ServiceLayer.OPERATION_SERVICE_TYPES

    @property
    def artifact_service_types(self):
        return ServiceLayer.ARTIFACT_SERVICE_TYPES

    def serviced_operation_types(self):
        return [ServicedOperationType(urn_prefix=service_type.URN_PREFIX,
                                      name=service_type.DEFAULT_NAME,
                                      description=service_type.DEFAULT_DESCRIPTION) for service_type in self.operation_service_types]

    @staticmethod
    def normal_artifact_type_urn_for(type_urn: str):
        if type_urn.startswith(":"):
            return models.Artifact.URN_PREFIX + type_urn
        return type_urn

    @staticmethod
    def normal_operation_type_urn_for(type_urn: str):
        if type_urn.startswith(":"):
            return models.Operation.URN_PREFIX + type_urn
        return type_urn

    def artifact_service(self, type_urn):
        type_urn = ServiceLayer.normal_artifact_type_urn_for(type_urn)
        for service_type in self.artifact_service_types:
            if type_urn == service_type.URN_PREFIX or type_urn.startswith(service_type.URN_PREFIX + ":"):
                return service_type(self.repo_layer)

    def operation_service(self, type_urn):
        type_urn = ServiceLayer.normal_operation_type_urn_for(type_urn)
        for service_type in self.operation_service_types:
            if type_urn == service_type.URN_PREFIX or type_urn.startswith(service_type.URN_PREFIX + ":"):
                return service_type(self.repo_layer)

    def create_default_operation(self, operation: models.Operation):
        for service_type in self.operation_service_types:
            if operation.type_urn.startswith(service_type.URN_PREFIX):
                return service_type(self.repo_layer).create_default(operation)

        raise UnservicedOperationTypeException(f"Operation of type {operation.type_urn} is not a serviced type.")

    def get_artifact_service(self, service_type, artifact: models.Artifact):
        if artifact.type_urn.startswith(service_type.URN_PREFIX):
            return service_type(self.repo_layer)

        raise UnservicedArtifactTypeException(f"Artifact of type {artifact.type_urn} is not compatible with service type {service_type}")

def init_request_service_layer(app: fastapi.FastAPI):

    def request_service_layer(repo_layer = Depends(repositories.request_repo_layer(app))):
        return ServiceLayer(repo_layer)

    app.state.services_request_service_layer = request_service_layer

def request_service_layer(app: fastapi.FastAPI) -> ServiceLayer:
    return app.state.services_request_service_layer