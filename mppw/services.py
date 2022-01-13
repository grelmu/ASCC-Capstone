from typing import Optional, List, ClassVar, Any
import fastapi
from fastapi import Depends
import fastapi.encoders
import pydantic
import bson
import datetime
import bson

from mppw import logger

from . import models
from . import repositories

DATABASE_BUCKET_URN_PREFIX = f"{models.DigitalArtifact.URN_PREFIX}:database-bucket"
FILE_BUCKET_URN_PREFIX = f"{models.DigitalArtifact.URN_PREFIX}:file-bucket"

class OperationServices:

    ARTIFACT_KIND_ATTACHMENTS = ":attachments"
    ARTIFACT_KIND_PROCESS_DATA = ":process-data"

    def __init__(self, repo_layer):
        self.repo_layer = repo_layer

    def create_default_attachments(self, scheme=None):

        attachments = models.DigitalArtifact(
            type_urn = FILE_BUCKET_URN_PREFIX,
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

    def create_default_process_data(self, scheme=None):

        process_data = models.DigitalArtifact(
            type_urn = DATABASE_BUCKET_URN_PREFIX,
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

FFF_URN_PREFIX = f"{models.Operation.URN_PREFIX}:fff"

class FffServices(OperationServices):

    STATUS_PENDING = "pending"

    ARTIFACT_KIND_OPERATOR_NOTES = ":operator-notes"
    ARTIFACT_KIND_OUTPUT_PARTS = ":output-parts"

    def __init__(self, repo_layer):
        self.repo_layer = repo_layer
    
    def create_default_fff_operation(self, name=None, description=None, tags=None, urn_suffix=None,
                                           start_at=None):

        urn_segments = [FFF_URN_PREFIX]
        if urn_suffix is not None:
            urn_segments.append(urn_suffix)

        if start_at is None:
            start_at = datetime.datetime.now()

        fff = models.Operation(
            type_urn = ":".join(urn_segments),
            name = name or f"FFF Operation ({start_at.isoformat})",
            description = description,
            tags = tags,
            start_at = start_at,
            status = FffServices.STATUS_PENDING)
        
        fff.artifact_transform_graph = [
            models.ArtifactTransform(
                kind_urn=FffServices.ARTIFACT_KIND_OPERATOR_NOTES,
            ),
            models.ArtifactTransform(
                kind_urn=FffServices.ARTIFACT_KIND_OUTPUT_PARTS,
            ),
            self.create_default_process_data(),
            self.create_default_attachments(),
        ]

        return self.repo_layer.operations.create(fff)

class ServiceLayer:

    def __init__(self, repo_layer):

        self.repo_layer = repo_layer

        self.fff = FffServices(self.repo_layer)

def init_request_service_layer(app: fastapi.FastAPI):

    def request_service_layer(repo_layer = Depends(repositories.request_repo_layer(app))):
        return ServiceLayer(repo_layer)

    app.state.services_request_service_layer = request_service_layer

def request_service_layer(app: fastapi.FastAPI) -> ServiceLayer:
    return app.state.services_request_service_layer