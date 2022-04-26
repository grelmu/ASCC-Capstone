from .. import OperationServices
from .. import ServiceLayer

from ... import models


class CharacterizeTensileTestServices(OperationServices):
    def init(
        self,
        operation: models.Operation,
        **kwargs,
    ):
        super().init(operation, **kwargs)

        if not list(operation.attachments.find_nodes_by_path(":sample")):

            sample_artifact = self._init_sample_artifact(operation)
            self.attach(
                operation, [":sample"], sample_artifact.id, models.AttachmentMode.OUTPUT
            )

        return operation

    def _init_sample_artifact(self, operation):

        sample_artifact = models.DigitalArtifact(
            type_urn=models.MaterialArtifact.URN_PREFIX + ":sample",
            project=operation.project,
            name="Test Sample",
            description="Sample containing all specimens under test",
        )

        sample_artifact = self.repo_layer.artifacts.create(sample_artifact)
        return ServiceLayer.artifact_services_for(sample_artifact).init(sample_artifact)
