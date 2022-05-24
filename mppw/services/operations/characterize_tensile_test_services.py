from pyparsing import Char
from .. import OperationServices
from .. import ServiceLayer

from ... import models


class CharacterizeTensileTestServices(OperationServices):

    SAMPLE_KIND_PATH = [":sample"]

    def init(
        self,
        operation: models.Operation,
        **kwargs,
    ):
        super().init(operation, **kwargs)

        if not list(operation.attachments.find_nodes_by_path(":sample")):

            sample_artifact = self._init_sample_artifact(operation)
            self.attach(
                operation,
                models.AttachmentGraph.AttachmentNode.build(
                    [":sample"], sample_artifact.id, models.AttachmentMode.OUTPUT
                ),
            )

        return operation

    def _init_sample_artifact(self, operation):

        sample_artifact = models.MaterialArtifact(
            type_urn=models.MaterialArtifact.URN_PREFIX + ":sample",
            project=operation.project,
            name="Test Sample",
            description="Sample containing all specimens under test",
        )

        sample_artifact = self.repo_layer.artifacts.create(sample_artifact)
        return self.service_layer.artifact_services_for(sample_artifact).init(
            sample_artifact
        )

    def get_default_sample_node(self, operation: models.Operation):
        return operation.attachments.find_node_by_path(
            CharacterizeTensileTestServices.SAMPLE_KIND_PATH
        )

    def get_default_sample_artifact(self, operation):

        sample_node = self.get_default_sample_node(operation)
        if sample_node is None:
            return None

        return self.repo_layer.artifacts.query_one(id=sample_node.artifact_id)
