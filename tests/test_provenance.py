import pytest
import json

from mppw import storage
from mppw import repositories
from mppw import services

from mppw import models
from mppw import schemas

from .fixtures_services import ServiceLayerContext

class TestManufacturingProcess:
    def __init__(self, storage_layer, test_project: models.Project):
        self.storage_layer = storage_layer
        self.test_project = test_project
        self._init()

    def _init(self):

        with ServiceLayerContext(self.storage_layer) as service_layer:

            artifact_repo: repositories.ArtifactRepository = (
                service_layer.repo_layer.artifacts
            )
            operation_repo: repositories.OperationRepository = (
                service_layer.repo_layer.operations
            )

            self.batch = artifact_repo.create(
                models.MaterialArtifact(
                    type_urn="urn:x-mfg:artifact:material:batch",
                    project=self.test_project.id,
                )
            )
            self.wall = artifact_repo.create(
                models.MaterialArtifact(
                    type_urn="urn:x-mfg:artifact:material:part",
                    project=self.test_project.id,
                )
            )
            self.fiducials = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:fiducial-points",
                    project=self.test_project.id,
                )
            )
            self.specimen = artifact_repo.create(
                models.MaterialArtifact(
                    type_urn="urn:x-mfg:artifact:material:part",
                    project=self.test_project.id,
                )
            )

            self.fff = operation_repo.create(
                models.Operation(
                    type_urn="urn:x-mfg:operation:fff", project=self.test_project.id
                )
            )

            self.cut = operation_repo.create(
                models.Operation(
                    type_urn="urn:x-mfg:operation:prepare:waterjetcut",
                    project=self.test_project.id,
                )
            )

            fff_services = service_layer.operation_services_for(self.fff)
            fff_services.attach(
                self.fff,
                models.AttachmentGraph.AttachmentNode.build(
                    [":input-materials"], self.batch.id, models.AttachmentMode.OUTPUT
                ),
            )
            fff_services.attach(
                self.fff,
                models.AttachmentGraph.AttachmentNode.build(
                    [":output-parts"], self.wall.id, models.AttachmentMode.OUTPUT
                ),
            )
            fff_services.attach(
                self.fff,
                models.AttachmentGraph.AttachmentNode.build(
                    [":output-parts", self.wall.id, ":part-geometry"],
                    self.fiducials.id,
                    models.AttachmentMode.OUTPUT,
                ),
            )

            cut_services = service_layer.operation_services_for(self.cut)
            cut_services.attach(
                self.cut,
                models.AttachmentGraph.AttachmentNode.build(
                    [":input-parts"], self.wall.id, models.AttachmentMode.INPUT
                ),
            )
            cut_services.attach(
                self.cut,
                models.AttachmentGraph.AttachmentNode.build(
                    [":input-parts", self.wall.id, ":output-parts"],
                    self.specimen.id,
                    models.AttachmentMode.OUTPUT,
                ),
            )


def test_basic_process_provenance(storage_layer, test_project):

    test_process = TestManufacturingProcess(storage_layer, test_project)

    with ServiceLayerContext(storage_layer) as service_layer:

        provenance_services = service_layer.provenance_services()

        # Backwards from specimen

        provenance = provenance_services.build_provenance(
            test_process.specimen.id, strategy="ancestors"
        )

        assert len(list(provenance.artifact_nodes())) == 3
        assert len(list(provenance.step_nodes())) == 2
        assert len(provenance.edges) == 4

        # Backwards from specimen with measurements

        provenance = provenance_services.build_provenance(
            test_process.specimen.id, strategy="ancestors+3"
        )

        assert len(list(provenance.artifact_nodes())) == 3 + 1
        assert len(list(provenance.step_nodes())) == 2 + 1
        assert len(provenance.edges) == 4 + 2

        provenance = provenance_services.build_provenance(
            test_process.batch.id, strategy="descendants"
        )

        # Forwards from batch

        assert len(list(provenance.artifact_nodes())) == 4
        assert len(list(provenance.step_nodes())) == 3
        assert len(provenance.edges) == 6

        # Forwards from wall

        provenance = provenance_services.build_provenance(
            test_process.wall.id, strategy="descendants"
        )

        assert len(list(provenance.artifact_nodes())) == 3
        assert len(list(provenance.step_nodes())) == 2
        assert len(provenance.edges) == 4

        # Forwards from wall with measurements

        provenance = provenance_services.build_provenance(
            test_process.wall.id, strategy="descendants+3"
        )

        assert len(list(provenance.artifact_nodes())) == 4
        assert len(list(provenance.step_nodes())) == 3
        assert len(provenance.edges) == 6
