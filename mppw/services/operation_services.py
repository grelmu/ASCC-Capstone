from doctest import OutputChecker
from typing import Optional, List, ClassVar, Any, Union, ForwardRef, Sequence, Tuple
import fastapi
from fastapi import Depends
import fastapi.encoders
import pydantic
import bson
import datetime
import bson
import furl

from mppw import logger

from .. import models
from .. import schemas


class NoStrategyFoundException(Exception):
    pass


class OperationServices:

    """
    The basic services that all operations share
    """

    AttachedArtifact = Tuple[
        models.AttachmentGraph.AttachmentNode, Optional[models.AnyArtifact]
    ]

    STATUS_DRAFT = "draft"

    PROCESS_DATA_KIND_PATH = [":process-data"]
    ATTACHMENTS_KIND_PATH = [":attachments"]

    DEFAULT_ATTACHMENTS_TYPE_URN = models.Artifact.URN_PREFIX + ":digital:file-bucket"
    DEFAULT_PROCESS_DATA_TYPE_URN = (
        models.Artifact.URN_PREFIX + ":digital:database-bucket"
    )

    def __init__(self, service_layer, schema: schemas.OperationSchema):

        from .service_layer import ServiceLayer

        self.service_layer: ServiceLayer = service_layer
        self.repo_layer = self.service_layer.repo_layer
        self.schema = schema

    @staticmethod
    def pretty_type_urn(type_urn: str):
        suffix = type_urn.replace(models.Operation.URN_PREFIX, "")
        suffix = suffix.split(":")[-1]
        return " ".join(map(str.capitalize, suffix.split("-")))

    @property
    def default_name(self):
        if self.schema.name:
            return self.schema.name
        return f"{self.pretty_type_urn(self.schema.type_urn)} Services"

    @property
    def default_description(self):
        if self.schema.description:
            return self.schema.description
        return None

    def init(
        self,
        operation: models.Operation,
        process_data_scheme=None,
        attachments_scheme=None,
        **kwargs,
    ):

        if not operation.name:
            operation.name = self.default_name

        if not operation.description:
            operation.description = self.default_description

        if operation.start_at is None:
            start_at = datetime.datetime.now()

        if not operation.status:
            operation.status = OperationServices.STATUS_DRAFT

        process_data_node = operation.attachments.find_node_by_path(
            OperationServices.PROCESS_DATA_KIND_PATH
        )

        if process_data_node is None:

            process_data_artifact = self._init_process_data_artifact(
                operation, process_data_scheme
            )

            operation.attachments.build_attachment_node(
                OperationServices.PROCESS_DATA_KIND_PATH,
                process_data_artifact.id,
                models.AttachmentMode.OUTPUT,
            )

        attachments_node = operation.attachments.find_node_by_path(
            OperationServices.ATTACHMENTS_KIND_PATH
        )

        if attachments_node is None:

            attachments_artifact = self._init_attachments_artifact(
                operation, attachments_scheme
            )

            operation.attachments.build_attachment_node(
                OperationServices.ATTACHMENTS_KIND_PATH,
                attachments_artifact.id,
                models.AttachmentMode.OUTPUT,
            )

        return operation if self.repo_layer.operations.update(operation) else None

    def _init_attachments_artifact(self, operation: models.Operation, scheme=None):

        attachments_artifact = models.DigitalArtifact(
            type_urn=OperationServices.DEFAULT_ATTACHMENTS_TYPE_URN,
            project=operation.project,
            name="Default Attachments",
        )

        attachments_services = self.service_layer.artifact_services_for(
            attachments_artifact
        )

        attachments_artifact = self.repo_layer.artifacts.create(attachments_artifact)
        return attachments_services.init(attachments_artifact, scheme=scheme)

    def _init_process_data_artifact(self, operation: models.Operation, scheme=None):

        process_data_artifact = models.DigitalArtifact(
            type_urn=OperationServices.DEFAULT_PROCESS_DATA_TYPE_URN,
            project=operation.project,
            name="Default Process Data",
        )

        process_data_services = self.service_layer.artifact_services_for(
            process_data_artifact
        )

        process_data_artifact = self.repo_layer.artifacts.create(process_data_artifact)
        return process_data_services.init(process_data_artifact, scheme=scheme)

    def get_default_attachments_node(self, operation: models.Operation):
        return operation.attachments.find_node_by_path(
            OperationServices.ATTACHMENTS_KIND_PATH
        )

    def get_default_attachments_artifact(self, operation: models.Operation):

        attachments_node = self.get_default_attachments_node(operation)
        if attachments_node is None:
            return None

        return self.repo_layer.artifacts.query_one(id=attachments_node.artifact_id)

    def attach(
        self,
        operation: models.Operation,
        attachment: models.AttachmentGraph.AttachmentNode,
    ) -> bool:

        operation.attachments.add_attachment_node(attachment)
        return self.repo_layer.operations.update(operation)

    def get_attached_artifacts(
        self,
        operation: models.Operation,
        kind_path=None,
        artifact_id=None,
        attachment_mode=None,
        parent_artifact_path=None,
    ) -> Sequence[AttachedArtifact]:

        for attachment_node in operation.attachments.find_nodes(
            kind_path=kind_path,
            artifact_id=artifact_id,
            attachment_mode=attachment_mode,
            parent_artifact_path=parent_artifact_path,
        ):
            if attachment_node.kind_path:
                yield (
                    attachment_node,
                    self.repo_layer.artifacts.query_one(id=attachment_node.artifact_id)
                    if attachment_node.artifact_id is not None
                    else None,
                )

    def claim(
        self,
        operation: models.Operation,
        attachment: models.AttachmentGraph.AttachmentNode,
    ) -> bool:

        """
        Tries to ensure that this operation attachment is the only "OUTPUT" attachment
        for the particular artifact.

        Iterates all the other operations with the same artifact attached and sets them
        to "INPUT", then rewrites the current attachment as "OUTPUT" mode.
        """

        if attachment not in operation.attachments.nodes():
            return False

        artifact_id = attachment.artifact_id

        def unclaim_artifact(operation: models.Operation):

            for other_attachment in list(
                operation.attachments.find_nodes_by_artifact(
                    artifact_id=artifact_id,
                    attachment_mode=models.AttachmentMode.OUTPUT,
                )
            ):
                operation.attachments.replace_attachment_node(
                    other_attachment,
                    models.AttachmentGraph.AttachmentNode.build(
                        other_attachment.kind_path,
                        other_attachment.artifact_id,
                        models.AttachmentMode.INPUT,
                    ),
                )

            return operation

        for other_operation in self.repo_layer.operations.query_by_attached(
            output_artifact_id=artifact_id
        ):
            other_operation: models.Operation
            if other_operation.id == operation.id:
                continue

            self.repo_layer.operations.partial_update(
                other_operation.id, unclaim_artifact
            )

        def claim_artifact(operation: models.Operation):

            operation = unclaim_artifact(operation)

            operation.attachments.replace_attachment_node(
                attachment,
                models.AttachmentGraph.AttachmentNode.build(
                    attachment.kind_path,
                    attachment.artifact_id,
                    models.AttachmentMode.OUTPUT,
                ),
            )

            return operation

        return self.repo_layer.operations.partial_update(operation.id, claim_artifact)

    def detach(
        self,
        operation: models.Operation,
        attachment: models.AttachmentGraph.AttachmentNode,
    ) -> bool:

        if attachment not in operation.attachments.nodes():
            return False

        operation.attachments.remove_attachment_node_and_descendants(attachment)
        return self.repo_layer.operations.update(operation)

    #
    # Specialized searches
    #

    def frame_candidates(
        self,
        operation: models.Operation,
        attachment: models.AttachmentGraph.AttachmentNode,
        strategy: str = None,
    ):

        if strategy is None:
            strategy = "operation_local"

        if strategy == "operation_local":
            return self.frame_candidates_operation_local(operation)
        else:
            raise NoStrategyFoundException(f"Could not understand strategy {strategy}")

    def frame_candidates_operation_local(
        self, operation: models.Operation
    ) -> Sequence[AttachedArtifact]:

        for attachment_node, artifact in self.get_attached_artifacts(operation):
            if artifact is None or not isinstance(artifact, models.DigitalArtifact):
                continue

            yield (attachment_node, artifact)
