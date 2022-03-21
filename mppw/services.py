from doctest import OutputChecker
from typing import Optional, List, ClassVar, Any, Union, ForwardRef
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

AttachmentKindRef = ForwardRef('AttachmentKind')

class ArtifactType(pydantic.BaseModel):
    type_urn: str
    child_kinds: List[AttachmentKindRef]

    @staticmethod
    def make(spec):
        if isinstance(spec, str):
            return ArtifactType(type_urn=spec, child_kinds=[])
        return ArtifactType(type_urn=spec[0], child_kinds=AttachmentKind.make(spec[1]))

class AttachmentKind(pydantic.BaseModel):
    kind_urn: str
    types: List[ArtifactType]

    @staticmethod
    def make(spec):
        kinds = []
        for kind_urn, types in spec.items():
            kind = AttachmentKind(kind_urn=kind_urn, types=[])
            for type in types:
                kind.types.append(ArtifactType.make(type))
            kinds.append(kind)

        return kinds

ArtifactType.update_forward_refs()

AttachmentNodeRef = ForwardRef('AttachmentNode')

class ArtifactNode(models.BaseJsonModel):
    artifact_id: Union[models.DbId, None]
    is_input: bool
    attachments: List[AttachmentNodeRef]

class AttachmentNode(models.BaseJsonModel):
    kind_urn: str
    artifacts: List[ArtifactNode]

    @staticmethod
    def unflatten(transforms: List[models.ArtifactTransform]) -> ArtifactNode:
        
        transforms = list(transforms or [])
        transforms.sort(key=lambda t: t.kind_urn)

        artifact_paths = {
            "": ArtifactNode(artifact_id=None, is_input=False, attachments=[])
        }
        for transform in transforms:
            
            attachment_path = transform.kind_urn.split(".")
            kind_urn = attachment_path[-1]

            attachment_node = AttachmentNode(kind_urn=kind_urn, artifacts=[])
            inputs, outputs = (transform.input_artifacts or [], transform.output_artifacts or [])
            for i, artifact_id in enumerate(inputs + outputs):
                artifact_node = ArtifactNode(artifact_id=artifact_id, is_input=(i < len(inputs)), attachments=[])
                attachment_node.artifacts.append(artifact_node)
                artifact_paths[transform.kind_urn + "." + str(artifact_id)] = artifact_node

            parent_artifact_node = artifact_paths.get(".".join(attachment_path[0:-1]))
            if not parent_artifact_node: continue
            parent_artifact_node.attachments.append(attachment_node)

        return artifact_paths[""]

ArtifactNode.update_forward_refs()

class NewAttachment(pydantic.BaseModel):
    kind_urn: str
    artifact_id: str
    is_input: bool

class FrameCandidate(models.BaseJsonModel):
    id: models.DbId
    name: Optional[str]
    kind_urn: str

class NoStrategyFoundException(Exception):
    pass

class OperationServices:

    STATUS_DRAFT = "draft"

    ATTACHMENT_KINDS: List[AttachmentKind] = AttachmentKind.make({
        ":process-data": [":digital:database-bucket", ":digital:file-bucket", ":digital:file", ":digital:fiducial-points"],
        ":attachments": [":digital:file-bucket", ":digital:file", "digital:text"],
    })

    ATTACHMENT_KIND_PROCESS_DATA = ATTACHMENT_KINDS[0]
    ATTACHMENT_KIND_ATTACHMENTS = ATTACHMENT_KINDS[1]

    def __init__(self, repo_layer):
        self.repo_layer = repo_layer

    @property
    def default_name(self):
        return type(self).__name__.replace("Services", "") + " Operation"

    @property
    def default_description(self):
        return None

    @staticmethod
    def is_compatible_kind(general_kind:str, specific_kind: str):
        return general_kind == specific_kind or specific_kind.startswith(general_kind + ":") 

    def find_attachments_by_kind(self, operation: models.Operation, kind_urn: str, parent_artifact_node: ArtifactNode = None) -> List[AttachmentNode]:

        artifacts_root = AttachmentNode.unflatten(operation.artifact_transform_graph) if parent_artifact_node is None else parent_artifact_node

        matching = []
        for attachment_node in artifacts_root.attachments:
            if kind_urn == attachment_node.kind_urn: matching.append(attachment_node)

        return matching

    def find_attachment_by_kind(self, operation: models.Operation, kind_urn: str, parent_artifact_node: ArtifactNode = None) -> AttachmentNode:
        return (self.find_attachments_by_kind(operation, kind_urn, parent_artifact_node=parent_artifact_node) or [None])[0]

    def find_artifact_at(self, operation: models.Operation, artifact_path: List[str] = []) -> ArtifactNode:
        
        artifact_node = AttachmentNode.unflatten(operation.artifact_transform_graph)

        def find_child_artifact(artifact_node: ArtifactNode, kind_urn, artifact_id) -> ArtifactNode:
            for attachment_node in artifact_node.attachments:
                if attachment_node.kind_urn == kind_urn:
                    for child_artifact_node in attachment_node.artifacts:
                        if str(child_artifact_node.artifact_id) == str(artifact_id): return child_artifact_node
            return None

        while artifact_node is not None and artifact_path:
            
            kind_urn, artifact_id = artifact_path[0:2]
            artifact_path = artifact_path[2:]
            artifact_node = find_child_artifact(artifact_node, kind_urn, artifact_id)

        return artifact_node

    def find_transform_by_kind(self, operation: models.Operation, kind_urn: str) -> models.ArtifactTransform:
        for transform in operation.artifact_transform_graph:
            if transform.kind_urn == kind_urn:
                return transform
        return None

    def init(self, operation: models.Operation, process_data_scheme=None, attachments_scheme=None, **kwargs):
        
        if not operation.name:
            operation.name = self.default_name

        if not operation.description:
            operation.description = self.default_description

        if operation.start_at is None:
            start_at = datetime.datetime.now()

        if not operation.status:
            operation.status = OperationServices.STATUS_DRAFT

        if operation.artifact_transform_graph is None:
            operation.artifact_transform_graph = []

        if self.find_attachment_by_kind(operation, OperationServices.ATTACHMENT_KIND_PROCESS_DATA.kind_urn) is None:
            
            process_data_artifact = self._init_process_data_artifact(operation, process_data_scheme)
            operation.artifact_transform_graph.append(models.ArtifactTransform(
                kind_urn = OperationServices.ATTACHMENT_KIND_PROCESS_DATA.kind_urn,
                output_artifacts = [process_data_artifact.id]
            ))

        if self.find_attachment_by_kind(operation, OperationServices.ATTACHMENT_KIND_ATTACHMENTS.kind_urn) is None:
            
            attachments_artifact = self._init_attachments_artifact(operation, attachments_scheme)
            operation.artifact_transform_graph.append(models.ArtifactTransform(
                kind_urn = OperationServices.ATTACHMENT_KIND_ATTACHMENTS.kind_urn,
                output_artifacts = [attachments_artifact.id]
            ))

        return operation if self.repo_layer.operations.update(operation) else None

    def _init_attachments_artifact(self, operation: models.Operation, scheme=None):

        attachments_artifact = models.DigitalArtifact(
            type_urn = FileBucketServices.URN_PREFIX,
            project = operation.project,
            name = "Default Attachments",
        )

        self.repo_layer.artifacts.create(attachments_artifact)
        artifact_service = FileBucketServices(self.repo_layer)
        artifact_service.init(attachments_artifact)

        return attachments_artifact

    def _init_process_data_artifact(self, operation: models.Operation, scheme=None):

        process_data_artifact = models.DigitalArtifact(
            type_urn = DatabaseBucketServices.URN_PREFIX,
            project = operation.project,
            name = "Default Process Data", 
        )

        self.repo_layer.artifacts.create(process_data_artifact)
        artifact_service = DatabaseBucketServices(self.repo_layer)
        artifact_service.init(process_data_artifact)

        return process_data_artifact

    def get_default_attachments_artifact(self, operation: models.Operation):
        attachment = self.find_attachment_by_kind(operation, OperationServices.ATTACHMENT_KIND_ATTACHMENTS.kind_urn)
        if not attachment: return None
        return self.repo_layer.artifacts.query_one(id=attachment.artifacts[0].artifact_id)

    def attach(self, operation: models.Operation, kind_urn: str, artifact_id: str, is_input: Optional[bool] = None, artifact_path: List[str] = None):
        
        if artifact_path is None: artifact_path = []
        if is_input is None: is_input = False

        if self.find_artifact_at(operation, artifact_path) is None: return None

        transform_kind = ".".join(artifact_path + [kind_urn])
        transform = self.find_transform_by_kind(operation, transform_kind)

        if transform is None:
            transform = models.ArtifactTransform(kind_urn=transform_kind, input_artifacts=[], output_artifacts=[])
            operation.artifact_transform_graph.append(transform)

        transform.input_artifacts = transform.input_artifacts or []
        transform.output_artifacts = transform.output_artifacts or []
        (transform.input_artifacts if is_input else transform.output_artifacts).append(artifact_id)
        
        return self.repo_layer.operations.update(operation)

    def detach(self, operation: models.Operation, kind_urn: str, artifact_id: str, is_input: Optional[bool] = None, artifact_path: List[str] = None):
        
        if artifact_path is None: artifact_path = []

        transform_kind = ".".join(artifact_path + [kind_urn])
        transform = self.find_transform_by_kind(operation, transform_kind)

        if transform is None: return None
        
        if (is_input is None or is_input):
            transform.input_artifacts = [id for id in transform.input_artifacts if not (artifact_id == str(id))]
        elif (is_input is None or not is_input):
            transform.output_artifacts = [id for id in transform.output_artifacts if not (artifact_id == str(id))]
        else:
            return None

        if not transform.input_artifacts and not transform.output_artifacts:
            operation.artifact_transform_graph = list(filter(lambda t: not t.kind_urn == transform.kind_urn, operation.artifact_transform_graph))

        child_transform_kind = ".".join(artifact_path + [kind_urn, artifact_id])
        operation.artifact_transform_graph = list(filter(lambda t: not t.kind_urn.startswith(child_transform_kind + "."), operation.artifact_transform_graph))

        return self.repo_layer.operations.update(operation)

    def frame_candidates(self, operation: models.Operation, artifact_path: List[str], strategy: str = None):
        
        if strategy is None: strategy = "operation_local"
        
        if strategy == "operation_local":
            return self.frame_candidates_operation_local(operation, artifact_path)
        else:
            raise NoStrategyFoundException(f"Could not understand strategy {strategy}")
    
    def frame_candidates_operation_local(self, operation: models.Operation, artifact_path: List[str]):
        
        for transform in operation.artifact_transform_graph:
            for artifact_id in ((transform.input_artifacts or []) + (transform.output_artifacts or [])):
                artifact = self.repo_layer.artifacts.query_one(id=artifact_id)
                if artifact is None: continue
                if not isinstance(artifact, models.DigitalArtifact): continue
                yield FrameCandidate(id=artifact.id, name=artifact.name, kind_urn=transform.kind_urn)

class FffServices(OperationServices):

    URN_PREFIX = f"{models.Operation.URN_PREFIX}:fff"
    DEFAULT_NAME = "FFF Manufacture"
    DEFAULT_DESCRIPTION = "FFF or FDM manufacturing operation"

    ATTACHMENT_KINDS = AttachmentKind.make({
        ":toolpath": [":digital:file"],
        ":input-materials": [
            (":material:batch", {
                ":notes" : [":digital:file", ":digital:text"],
            }),
        ],
        ":output-parts": [
            (":material:part", {
                ":part-geometry" : [":digital:fiducial-points"],
                ":images" : [":digital:file"],
                ":notes" : [":digital:file", ":digital:text"],
            }),
        ],
        ":operator-notes": [":digital:file", ":digital:text"],
        ":toolpath-cloud": [
            (":digital:point-cloud", {
                ":generation-notes" : [":digital:text"],
            }),
        ],
        ":thermal-cloud": [
            (":digital:point-cloud", {
                ":generation-notes" : [":digital:text"],
            }),
        ],
    })

    def __init__(self, repo_layer):
        self.repo_layer = repo_layer
    
    @property
    def attachment_kinds(self):
        return FffServices.ATTACHMENT_KINDS + OperationServices.ATTACHMENT_KINDS

class ArtifactServices:

    def __init__(self, repo_layer):
        self.repo_layer = repo_layer

    def init(self, artifact: models.DigitalArtifact, **kwargs):
        return artifact

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

        if not self.repo_layer.artifacts.update(artifact):
            return None
        return artifact

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

    @staticmethod
    def is_compatible_type(generic_type: str, specific_type: str):
        return generic_type == specific_type or specific_type.startswith(generic_type + ":")

    def serviced_operation_types(self):
        return [ServicedOperationType(urn_prefix=service_type.URN_PREFIX,
                                      name=service_type.DEFAULT_NAME,
                                      description=service_type.DEFAULT_DESCRIPTION) for service_type in self.operation_service_types]

    def artifact_services_for(self, type_urn) -> ArtifactServices:
        if isinstance(type_urn, models.Artifact):
            type_urn = type_urn.type_urn
        type_urn = ServiceLayer.normal_artifact_type_urn_for(type_urn)
        for service_type in self.artifact_service_types:
            if ServiceLayer.is_compatible_type(service_type.URN_PREFIX, type_urn):
                return service_type(self.repo_layer)
        return ArtifactServices(self.repo_layer)

    def artifact_service(self, type_urn):
        return self.artifact_services_for(type_urn)

    def operation_services_for(self, type_urn) -> OperationServices:
        if isinstance(type_urn, models.Operation):
            type_urn = type_urn.type_urn
        type_urn = ServiceLayer.normal_operation_type_urn_for(type_urn)
        for service_type in self.operation_service_types:
            if ServiceLayer.is_compatible_type(service_type.URN_PREFIX, type_urn):
                return service_type(self.repo_layer) 
        return OperationServices(self.repo_layer)

    def operation_service(self, type_urn):
        return self.operation_services_for(type_urn)

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