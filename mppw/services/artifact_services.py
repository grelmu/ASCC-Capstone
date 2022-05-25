from typing import List, Optional

from mppw import logger

from .. import models
from .. import schemas


class ArtifactServices:

    """
    The basic services that all artifacts share
    """

    def __init__(
        self,
        service_layer,
        schema: schemas.ArtifactSchema,
    ):
        from .service_layer import ServiceLayer

        self.service_layer: ServiceLayer = service_layer
        self.repo_layer = self.service_layer.repo_layer
        self.schema = schema

    def init(self, artifact: models.AnyArtifact, **kwargs):
        return artifact

    def operation_parents(self, artifact: models.AnyArtifact) -> List[models.Operation]:
        return self.repo_layer.operations.query_by_attached(
            output_artifact_id=str(artifact.id), project_ids=[str(artifact.project)]
        )

    def operation_parent(
        self, artifact: models.AnyArtifact
    ) -> Optional[models.Operation]:
        return (list(self.operation_parents(artifact)) or [None])[0]
