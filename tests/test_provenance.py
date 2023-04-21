import pytest
import json

from mppw import storage
from mppw import repositories
from mppw import services

from mppw import models
from mppw import schemas
from mppw import services

from .fixtures_services import ServiceLayerContext

"""
Unit tests of provenance services
"""


class TestBasicManufacturingProcess:

    """
    A basic manufacturing process used to check core provenance functionality

    Builds a minimal :fff operation with input batch, output part and a
    :waterjetcut operation with input part and output cut part.
    """

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
    """
    Test provenance exploration of a basic process
    """

    test_process = TestBasicManufacturingProcess(storage_layer, test_project)

    with ServiceLayerContext(storage_layer) as service_layer:
        provenance_services = service_layer.provenance_services()

        # Backwards from specimen

        provenance = provenance_services.build_artifact_provenance(
            test_process.specimen.id, strategy="ancestors"
        )

        assert len(list(provenance.artifact_nodes())) == 3
        assert len(list(provenance.step_nodes())) == 2
        assert len(provenance.edges) == 4

        # Backwards from specimen with measurements

        provenance = provenance_services.build_artifact_provenance(
            test_process.specimen.id, strategy="ancestors+3"
        )

        assert len(list(provenance.artifact_nodes())) == 3 + 1
        assert len(list(provenance.step_nodes())) == 2 + 1
        assert len(provenance.edges) == 4 + 2

        provenance = provenance_services.build_artifact_provenance(
            test_process.batch.id, strategy="descendants"
        )

        # Forwards from batch

        assert len(list(provenance.artifact_nodes())) == 4
        assert len(list(provenance.step_nodes())) == 3
        assert len(provenance.edges) == 6

        # Forwards from wall

        provenance = provenance_services.build_artifact_provenance(
            test_process.wall.id, strategy="descendants"
        )

        assert len(list(provenance.artifact_nodes())) == 3
        assert len(list(provenance.step_nodes())) == 2
        assert len(provenance.edges) == 4

        # Forwards from wall with measurements

        provenance = provenance_services.build_artifact_provenance(
            test_process.wall.id, strategy="descendants+3"
        )

        assert len(list(provenance.artifact_nodes())) == 4
        assert len(list(provenance.step_nodes())) == 3
        assert len(provenance.edges) == 6


class TestProcessPropertyManufacturingProcess:

    """
    A process/property manufacturing process used to check that we can explore from
    properties back to the build processes that made the specimens.

    Creates an FFF operation with two input batches and three output parts,
    which are then cut in three :waterjetcut operations into six specimen parts.
    The specimens are then grouped into two :tensile-test operations into samples
    which are then tested and computed properties added for each specimen and sample.
    """

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

            self.fff = operation_repo.create(
                models.Operation(
                    type_urn="urn:x-mfg:operation:fff",
                    project=self.test_project.id,
                    name="Process-Property FFF",
                )
            )

            fff_services = service_layer.operation_services_for(self.fff)
            fff_services.init(self.fff)

            self.batches = []
            for batch_name in ["Batch B1", "Batch B2"]:
                batch = artifact_repo.create(
                    models.MaterialArtifact(
                        type_urn="urn:x-mfg:artifact:material:batch",
                        project=self.test_project.id,
                        name=batch_name,
                    )
                )
                self.batches.append(batch)

                fff_services.attach(
                    self.fff,
                    models.AttachmentGraph.AttachmentNode.build(
                        [":input-materials"],
                        batch.id,
                        models.AttachmentMode.OUTPUT,
                    ),
                )

            self.walls = []

            for wall_name in ["Wall WA", "Wall WB", "Wall WC"]:
                wall_code = wall_name.split(" ")[-1]

                wall = artifact_repo.create(
                    models.MaterialArtifact(
                        type_urn="urn:x-mfg:artifact:material:part",
                        project=self.test_project.id,
                        name=wall_name,
                    )
                )
                self.walls.append(wall)

                image = artifact_repo.create(
                    models.DigitalArtifact(
                        type_urn="urn:x-mfg:artifact:digital:file",
                        project=self.test_project.id,
                        name=f"Image {wall_name}",
                    )
                )

                fiducials = artifact_repo.create(
                    models.DigitalArtifact(
                        type_urn="urn:x-mfg:artifact:digital:fiducial-points",
                        project=self.test_project.id,
                        name=f"Fiducials {wall_name}",
                    )
                )

                fff_services.attach(
                    self.fff,
                    models.AttachmentGraph.AttachmentNode.build(
                        [":output-parts"],
                        wall.id,
                        models.AttachmentMode.OUTPUT,
                    ),
                )

                fff_services.attach(
                    self.fff,
                    models.AttachmentGraph.AttachmentNode.build(
                        [":output-parts", wall.id, ":images"],
                        image.id,
                        models.AttachmentMode.OUTPUT,
                    ),
                )

                fff_services.attach(
                    self.fff,
                    models.AttachmentGraph.AttachmentNode.build(
                        [":output-parts", wall.id, ":part-geometry"],
                        fiducials.id,
                        models.AttachmentMode.OUTPUT,
                    ),
                )

            self.cuts = []
            self.specimens = []

            for wall in self.walls:
                wall_code = wall.name.split(" ")[-1]

                cut = operation_repo.create(
                    models.Operation(
                        type_urn="urn:x-mfg:operation:prepare:waterjetcut",
                        project=self.test_project.id,
                        name=f"Process-Property Cut {wall_code}",
                    )
                )
                self.cuts.append(cut)

                cut_services = service_layer.operation_services_for(cut)
                cut_services.init(cut)

                cut_services.attach(
                    cut,
                    models.AttachmentGraph.AttachmentNode.build(
                        [":input-parts"], wall.id, models.AttachmentMode.INPUT
                    ),
                )

                for specimen_name in [
                    f"Specimen {wall_code}_SA",
                    f"Specimen {wall_code}_SB",
                ]:
                    specimen = artifact_repo.create(
                        models.MaterialArtifact(
                            type_urn="urn:x-mfg:artifact:material:part",
                            project=self.test_project.id,
                            name=specimen_name,
                        )
                    )

                    self.specimens.append(specimen)

                    cut_services.attach(
                        cut,
                        models.AttachmentGraph.AttachmentNode.build(
                            [":input-parts", wall.id, ":output-parts"],
                            specimen.id,
                            models.AttachmentMode.OUTPUT,
                        ),
                    )

            self.tests = []
            self.test_specimens = {}
            self.specimen_dimensions = {}
            self.specimen_frames = {}
            self.specimen_properties = {}
            self.properties = []

            for test_index, test_name in enumerate(
                [
                    "Process-Property Tensile Test X",
                    "Process-Property Tensile Test Y",
                ]
            ):
                test_code = test_name.split(" ")[-1]

                test = operation_repo.create(
                    models.Operation(
                        type_urn="urn:x-mfg:operation:characterize:tensile-test",
                        project=self.test_project.id,
                        name=test_name,
                    )
                )
                self.tests.append(test)

                tt_services = service_layer.operation_services_for(test)
                tt_services.init(test)

                sample = tt_services.get_default_sample_artifact(test)

                test_specimens = [
                    s for i, s in enumerate(self.specimens) if i % 2 == test_index
                ]
                self.test_specimens[test.id] = test_specimens

                for test_specimen in test_specimens:
                    tt_services.attach(
                        test,
                        models.AttachmentGraph.AttachmentNode.build(
                            [":sample", sample.id, ":specimens"],
                            test_specimen.id,
                            models.AttachmentMode.INPUT,
                        ),
                    )

                    dimensions = artifact_repo.create(
                        models.DigitalArtifact(
                            type_urn="urn:x-mfg:artifact:digital:document:named-dimensions",
                            project=self.test_project.id,
                            name=f"Dimensions {test_specimen.name}",
                        )
                    )
                    self.specimen_dimensions[test_specimen.id] = dimensions

                    frame = artifact_repo.create(
                        models.DigitalArtifact(
                            type_urn="urn:x-mfg:artifact:digital:frame:force-displacement",
                            project=self.test_project.id,
                            name=f"Displacement {test_specimen.name}",
                        )
                    )
                    self.specimen_frames[test_specimen.id] = frame

                    properties = artifact_repo.create(
                        models.DigitalArtifact(
                            type_urn="urn:x-mfg:artifact:digital:document:tensile-properties",
                            project=self.test_project.id,
                            name=f"Properties {test_specimen.name}",
                        )
                    )
                    self.specimen_properties[test_specimen.id] = properties

                    tt_services.attach(
                        test,
                        models.AttachmentGraph.AttachmentNode.build(
                            [
                                ":sample",
                                sample.id,
                                ":specimens",
                                test_specimen.id,
                                ":test-dimensions",
                            ],
                            dimensions.id,
                            models.AttachmentMode.OUTPUT,
                        ),
                    )

                    tt_services.attach(
                        test,
                        models.AttachmentGraph.AttachmentNode.build(
                            [
                                ":sample",
                                sample.id,
                                ":specimens",
                                test_specimen.id,
                                ":test-measurements",
                            ],
                            frame.id,
                            models.AttachmentMode.OUTPUT,
                        ),
                    )

                    tt_services.attach(
                        test,
                        models.AttachmentGraph.AttachmentNode.build(
                            [
                                ":sample",
                                sample.id,
                                ":specimens",
                                test_specimen.id,
                                ":computed-properties",
                            ],
                            properties.id,
                            models.AttachmentMode.OUTPUT,
                        ),
                    )

                properties = artifact_repo.create(
                    models.DigitalArtifact(
                        type_urn="urn:x-mfg:artifact:digital:document:tensile-properties",
                        project=self.test_project.id,
                        name=f"Properties {sample.name}",
                    )
                )
                self.properties.append(properties)

                tt_services.attach(
                    test,
                    models.AttachmentGraph.AttachmentNode.build(
                        [":sample", sample.id, ":computed-properties"],
                        properties.id,
                        models.AttachmentMode.OUTPUT,
                    ),
                )


def test_process_property_provenance(storage_layer, test_project):
    """
    Tests that we can explore a full process-property provenance
    """

    test_process = TestProcessPropertyManufacturingProcess(storage_layer, test_project)

    with ServiceLayerContext(storage_layer) as service_layer:
        provenance_services = service_layer.provenance_services()

        # Backwards from sample properties

        provenance = provenance_services.build_artifact_provenance(
            test_process.properties[0].id, strategy="ancestors"
        )

        assert len(list(provenance.artifact_nodes())) == 10
        assert len(list(provenance.step_nodes())) == 6

        # Backwards from specimen properties

        test_specimens = test_process.test_specimens[test_process.tests[0].id]
        specimen_properties = test_process.specimen_properties[test_specimens[0].id].id

        provenance = provenance_services.build_artifact_provenance(
            specimen_properties.id, strategy="ancestors"
        )

        assert len(list(provenance.artifact_nodes())) == 5
        assert len(list(provenance.step_nodes())) == 3

        # Backwards from specimen dimensions

        specimen_dimensions = test_process.specimen_dimensions[test_specimens[0].id].id

        provenance = provenance_services.build_artifact_provenance(
            specimen_dimensions.id, strategy="ancestors"
        )

        assert len(list(provenance.artifact_nodes())) == 5
        assert len(list(provenance.step_nodes())) == 3

        # Backwards from specimen frame

        specimen_frame = test_process.specimen_frames[test_specimens[0].id].id

        provenance = provenance_services.build_artifact_provenance(
            specimen_frame.id, strategy="ancestors"
        )

        assert len(list(provenance.artifact_nodes())) == 5
        assert len(list(provenance.step_nodes())) == 3


class TestFrameGraph:

    """
    A basic frame graph used to check geometric provenance

    Builds a minimal set of artifacts with a root :toolpath directly attached to a :cloud measurement
    alongside another :cloud measurement indirectly attached via :fiducial-points
    """

    def __init__(
        self, storage_layer, test_project: models.Project, attach_to_operation=False
    ):
        self.storage_layer = storage_layer
        self.test_project = test_project
        self.attach_to_operation = attach_to_operation
        self._init()

    def _init(self):
        with ServiceLayerContext(self.storage_layer) as service_layer:
            artifact_repo: repositories.ArtifactRepository = (
                service_layer.repo_layer.artifacts
            )

            self.toolpath: models.DigitalArtifact = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:file",
                    project=self.test_project.id,
                )
            )

            self.cloud: models.DigitalArtifact = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:point-cloud",
                    project=self.test_project.id,
                )
            )

            self.cloud.spatial_frame = models.SpatialFrame(
                parent_frame=self.toolpath.id, transform={"x": 1}
            )
            artifact_repo.update(self.cloud)

            self.fiducials: models.DigitalArtifact = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:fiducial-points",
                    project=self.test_project.id,
                )
            )

            self.fiducials.spatial_frame = models.SpatialFrame(
                parent_frame=self.toolpath.id, transform={"x": 2}
            )
            artifact_repo.update(self.fiducials)

            self.mesh: models.DigitalArtifact = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:mesh",
                    project=self.test_project.id,
                )
            )

            self.mesh.spatial_frame = models.SpatialFrame(
                parent_frame=self.fiducials.id, transform={"x": 3}
            )
            artifact_repo.update(self.mesh)

            self.mesh2: models.DigitalArtifact = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:mesh",
                    project=self.test_project.id,
                )
            )

            self.mesh2.spatial_frame = models.SpatialFrame(
                parent_frame=self.fiducials.id, transform={"x": 4}
            )
            artifact_repo.update(self.mesh2)

            # Mesh 3 is *not* related spatially to any other artifact
            self.mesh3: models.DigitalArtifact = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:mesh",
                    project=self.test_project.id,
                )
            )

            if self.attach_to_operation:
                operation_repo: repositories.OperationRepository = (
                    service_layer.repo_layer.operations
                )

                self.fff = operation_repo.create(
                    models.Operation(
                        type_urn="urn:x-mfg:operation:fff",
                        project=self.test_project.id,
                        name="Frame Graph FFF",
                    )
                )

                fff_services = service_layer.operation_services_for(self.fff)
                fff_services.init(self.fff)

                self.wall = artifact_repo.create(
                    models.MaterialArtifact(
                        type_urn="urn:x-mfg:artifact:material:part",
                        project=self.test_project.id,
                    )
                )

                for kind_path, artifact in [
                    ([":toolpath"], self.toolpath),
                    ([":thermal-cloud"], self.cloud),
                    ([":output-parts"], self.wall),
                    (
                        [":output-parts", str(self.wall.id), ":part-geometry"],
                        self.fiducials,
                    ),
                    ([":output-parts", str(self.wall.id), ":part-geometry"], self.mesh),
                    (
                        [":output-parts", str(self.wall.id), ":part-geometry"],
                        self.mesh2,
                    ),
                    (
                        [":output-parts", str(self.wall.id), ":part-geometry"],
                        self.mesh3,
                    ),
                ]:
                    fff_services.attach(
                        self.fff,
                        models.AttachmentGraph.AttachmentNode.build(
                            kind_path,
                            artifact.id,
                            models.AttachmentMode.OUTPUT,
                        ),
                    )


def test_basic_frame_graph(storage_layer, test_project):
    """
    Tests that we can generate a full artifact frame graph
    """

    test_frame_graph = TestFrameGraph(storage_layer, test_project)

    with ServiceLayerContext(storage_layer) as service_layer:
        provenance_services = service_layer.provenance_services()

        # Full from mesh

        frame_graph = provenance_services.build_artifact_frame_graph(
            test_frame_graph.mesh.id, strategy="full"
        )

        assert len(list(frame_graph.nodes())) == 5
        assert len(list(frame_graph.edges())) == 4

        toolpath_node = services.provenance_services.ArtifactFrameGraph.ArtifactNode(
            artifact_id=str(test_frame_graph.toolpath.id)
        )
        cloud_node = services.provenance_services.ArtifactFrameGraph.ArtifactNode(
            artifact_id=str(test_frame_graph.cloud.id)
        )
        fiducials_node = services.provenance_services.ArtifactFrameGraph.ArtifactNode(
            artifact_id=str(test_frame_graph.fiducials.id)
        )

        assert len(list(frame_graph.out_edges([toolpath_node]))) == 2
        assert len(list(frame_graph.out_edges([fiducials_node]))) == 2
        assert len(list(frame_graph.out_edges([cloud_node]))) == 0


def test_explore_frame_graph(storage_layer, test_project):
    """
    Tests that we can explore parents/children of a artifact frame graph
    """

    test_frame_graph = TestFrameGraph(storage_layer, test_project)

    with ServiceLayerContext(storage_layer) as service_layer:
        provenance_services = service_layer.provenance_services()

        # Parents from mesh

        frame_graph = provenance_services.build_artifact_frame_graph(
            test_frame_graph.mesh.id, strategy="parents"
        )

        assert len(list(frame_graph.nodes())) == 3
        assert len(list(frame_graph.edges())) == 2

        # Children from mesh

        frame_graph = provenance_services.build_artifact_frame_graph(
            test_frame_graph.mesh.id, strategy="children"
        )

        assert len(list(frame_graph.nodes())) == 0
        assert len(list(frame_graph.edges())) == 0

        # Parents from fiducials

        frame_graph = provenance_services.build_artifact_frame_graph(
            test_frame_graph.fiducials.id, strategy="parents"
        )

        assert len(list(frame_graph.nodes())) == 2
        assert len(list(frame_graph.edges())) == 1

        # Children from fiducials

        frame_graph = provenance_services.build_artifact_frame_graph(
            test_frame_graph.fiducials.id, strategy="children"
        )

        assert len(list(frame_graph.nodes())) == 3
        assert len(list(frame_graph.edges())) == 2

        # Parents from toolpath

        frame_graph = provenance_services.build_artifact_frame_graph(
            test_frame_graph.toolpath.id, strategy="parents"
        )

        assert len(list(frame_graph.nodes())) == 0
        assert len(list(frame_graph.edges())) == 0

        # Children from toolpath

        frame_graph = provenance_services.build_artifact_frame_graph(
            test_frame_graph.toolpath.id, strategy="children"
        )

        assert len(list(frame_graph.nodes())) == 5
        assert len(list(frame_graph.edges())) == 4

        # Full from mesh3

        frame_graph = provenance_services.build_artifact_frame_graph(
            test_frame_graph.mesh3.id, strategy="full"
        )

        assert len(list(frame_graph.nodes())) == 0
        assert len(list(frame_graph.edges())) == 0


def test_explore_frame_path(storage_layer, test_project):
    """
    Tests that we can explore paths between artifacts in frame graphs
    """

    test_frame_graph = TestFrameGraph(storage_layer, test_project)

    with ServiceLayerContext(storage_layer) as service_layer:
        provenance_services = service_layer.provenance_services()

        # Mesh to Cloud

        frame_path = provenance_services.build_artifact_frame_path(
            test_frame_graph.mesh.id, test_frame_graph.cloud.id
        )

        toolpath_node = services.provenance_services.ArtifactFrameGraph.ArtifactNode(
            artifact_id=str(test_frame_graph.toolpath.id)
        )
        cloud_node = services.provenance_services.ArtifactFrameGraph.ArtifactNode(
            artifact_id=str(test_frame_graph.cloud.id)
        )
        mesh_node = services.provenance_services.ArtifactFrameGraph.ArtifactNode(
            artifact_id=str(test_frame_graph.mesh.id)
        )
        mesh2_node = services.provenance_services.ArtifactFrameGraph.ArtifactNode(
            artifact_id=str(test_frame_graph.mesh2.id)
        )

        assert len(list(frame_path.nodes())) == 4
        assert len(list(frame_path.edges())) == 3
        assert frame_path.path_nodes[0] == mesh_node
        assert frame_path.path_nodes[-1] == cloud_node

        # Cloud to Mesh

        frame_path = provenance_services.build_artifact_frame_path(
            test_frame_graph.cloud.id, test_frame_graph.mesh.id
        )

        assert len(list(frame_path.nodes())) == 4
        assert len(list(frame_path.edges())) == 3
        assert frame_path.path_nodes[0] == cloud_node
        assert frame_path.path_nodes[-1] == mesh_node

        # Mesh to Mesh2

        frame_path = provenance_services.build_artifact_frame_path(
            test_frame_graph.mesh.id, test_frame_graph.mesh2.id
        )

        assert len(list(frame_path.nodes())) == 3
        assert len(list(frame_path.edges())) == 2
        assert frame_path.path_nodes[0] == mesh_node
        assert frame_path.path_nodes[-1] == mesh2_node

        # Cloud to Toolpath

        frame_path = provenance_services.build_artifact_frame_path(
            test_frame_graph.cloud.id, test_frame_graph.toolpath.id
        )

        assert len(list(frame_path.nodes())) == 2
        assert len(list(frame_path.edges())) == 1
        assert frame_path.path_nodes[0] == cloud_node
        assert frame_path.path_nodes[-1] == toolpath_node

        # Toolpath to mesh3

        frame_path = provenance_services.build_artifact_frame_path(
            test_frame_graph.toolpath.id, test_frame_graph.mesh3.id
        )

        assert frame_path is None


class TestBasicManufacturingProcessWithGeometry(TestBasicManufacturingProcess):

    """
    A basic manufacturing process used to check geometric search provenance functionality
    """

    def __init__(self, storage_layer, test_project: models.Project):
        super().__init__(storage_layer, test_project)
        self._init_geometry()

    def _init_geometry(self):
        with ServiceLayerContext(self.storage_layer) as service_layer:
            artifact_repo: repositories.ArtifactRepository = (
                service_layer.repo_layer.artifacts
            )

            operation_repo: repositories.OperationRepository = (
                service_layer.repo_layer.operations
            )

            self.toolpath = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:file",
                    project=self.test_project.id,
                )
            )

            self.thermal_cloud = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:point-cloud",
                    project=self.test_project.id,
                )
            )

            self.thermal_cloud.spatial_frame = models.SpatialFrame(
                parent_frame=self.toolpath.id, transform={}
            )
            artifact_repo.update(self.thermal_cloud)

            self.fiducials.spatial_frame = models.SpatialFrame(
                parent_frame=self.toolpath.id, transform={}
            )
            artifact_repo.update(self.fiducials)

            fff_services = service_layer.operation_services_for(self.fff)
            fff_services.attach(
                self.fff,
                models.AttachmentGraph.AttachmentNode.build(
                    [":toolpath"],
                    self.toolpath.id,
                    models.AttachmentMode.OUTPUT,
                ),
            )
            fff_services.attach(
                self.fff,
                models.AttachmentGraph.AttachmentNode.build(
                    [":thermal-cloud"],
                    self.thermal_cloud.id,
                    models.AttachmentMode.OUTPUT,
                ),
            )

            self.specimen_bbox = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:document:bounding-box",
                    project=self.test_project.id,
                )
            )

            self.specimen_bbox.spatial_frame = models.SpatialFrame(
                parent_frame=self.fiducials.id, transform={}
            )
            artifact_repo.update(self.specimen_bbox)

            cut_services = service_layer.operation_services_for(self.cut)
            cut_services.attach(
                self.cut,
                models.AttachmentGraph.AttachmentNode.build(
                    [
                        ":input-parts",
                        self.wall.id,
                        ":output-parts",
                        self.specimen.id,
                        ":part-geometry",
                    ],
                    self.specimen_bbox.id,
                    models.AttachmentMode.OUTPUT,
                ),
            )


def test_explore_ancestor_frame_path(storage_layer, test_project):
    """
    Tests that we can explore paths between ancestor artifacts in frame graphs
    """

    process_with_geometry = TestBasicManufacturingProcessWithGeometry(
        storage_layer, test_project
    )

    with ServiceLayerContext(storage_layer) as service_layer:
        provenance_services = service_layer.provenance_services()

        # Mesh to Cloud

        ancestor_frame_paths = provenance_services.build_artifact_ancestor_frame_paths(
            process_with_geometry.thermal_cloud.id, process_with_geometry.specimen.id
        )

        bbox_frame_path, bbox_provenance_path = ancestor_frame_paths[0]

        assert bbox_frame_path.path_nodes[0].artifact_id == str(
            process_with_geometry.thermal_cloud.id
        )
        assert bbox_frame_path.path_nodes[1].artifact_id == str(
            process_with_geometry.toolpath.id
        )
        assert bbox_frame_path.path_nodes[2].artifact_id == str(
            process_with_geometry.fiducials.id
        )
        assert bbox_frame_path.path_nodes[3].artifact_id == str(
            process_with_geometry.specimen_bbox.id
        )

        assert bbox_provenance_path.path_nodes[0].artifact_id == str(
            process_with_geometry.specimen_bbox.id
        )
        assert bbox_provenance_path.path_nodes[2].artifact_id == str(
            process_with_geometry.specimen.id
        )

        assert [
            len(provenance_path)
            for frame_path, provenance_path in ancestor_frame_paths[1:]
        ] == [5, 5, 5]


def test_query_provenance(storage_layer, test_project):
    """
    Tests that we can explore paths between ancestor artifacts in frame graphs
    """

    process_with_geometry = TestBasicManufacturingProcessWithGeometry(
        storage_layer, test_project
    )

    with ServiceLayerContext(storage_layer) as service_layer:
        provenance_services: services.ProvenanceServices = (
            service_layer.provenance_services()
        )

        results = provenance_services.query_artifact_provenance(
            [process_with_geometry.specimen.id, process_with_geometry.wall.id],
            """
                MATCH (TC:ArtifactNode)<--(FFF:OperationStepNode)-[*1..99]->(CUT:OperationStepNode)-->(S:ArtifactNode) 
                WHERE
                    TC.type_urn = "urn:x-mfg:artifact:digital:point-cloud" AND
                    FFF.type_urn = "urn:x-mfg:operation:fff" AND
                    CUT.type_urn = "urn:x-mfg:operation:prepare:waterjetcut" AND
                    S.type_urn = "urn:x-mfg:artifact:material:part"
                RETURN TC, S
            """,
            strategy="ancestors+2",
        )

        assert results[0]["TC"][0].artifact_id == str(
            process_with_geometry.thermal_cloud.id
        )
        assert results[0]["S"][0].artifact_id == str(process_with_geometry.specimen.id)

        (
            provenance_path,
            frame_path,
        ) = provenance_services.build_nearest_related_artifact_frame_path(
            results[0]["S"][0].artifact_id,
            """
                MATCH (P:ArtifactNode)-->()-->(B:ArtifactNode) 
                WHERE
                    P.type_urn = "urn:x-mfg:artifact:material:part" AND
                    B.type_urn = "urn:x-mfg:artifact:digital:document:bounding-box"
                RETURN B
            """,
            results[0]["TC"][0].artifact_id,
            strategy="ancestors+2",
        )

        assert provenance_path.path_nodes[0].artifact_id == str(
            process_with_geometry.specimen.id
        )
        assert provenance_path.path_nodes[-1].artifact_id == str(
            process_with_geometry.specimen_bbox.id
        )
        assert frame_path.path_nodes[0].artifact_id == str(
            process_with_geometry.specimen_bbox.id
        )
        assert frame_path.path_nodes[-1].artifact_id == str(
            process_with_geometry.thermal_cloud.id
        )
