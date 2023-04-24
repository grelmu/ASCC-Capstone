import numpy

from mppw import repositories
from mppw import models

from mppw.services.artifacts.digital_bounding_box_services import (
    BoundingBoxServices,
)

from .fixtures_services import ServiceLayerContext


"""
Unit tests of provenance services
"""


class TestFrameRelatedArtifacts:

    """
    A basic manufacturing process used to check transform functionality
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

            #
            # Wall printed at (x=1000, y=1000, z=0) to (x=1010, y=2000, z=1010) with 10mm high brim
            #
            #        []
            #        [] <- pics and measurements this side
            #   y    []
            #   ^
            #   |
            #   .___>x
            #

            self.toolpath = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:file",
                    project=self.test_project.id,
                )
            )

            #
            # Fiducial coordinates moved and rotated to *front* corner of wall
            # relative to pics with y now vertical and z toward the camera
            #

            self.thermal_cloud = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:point-cloud",
                    project=self.test_project.id,
                    spatial_frame=models.SpatialFrame(
                        parent_frame=self.toolpath.id,
                        transform={
                            "translation_xyz": {"x": 1010, "y": 1000, "z": 10},
                            "rotation_euler_abg": {
                                "a": numpy.pi / 2.0,  # Z
                                "b": 0,  # Y
                                "g": numpy.pi / 2.0,  # X
                            },
                        },
                    ),
                )
            )

            #
            # Fiducial coordinates moved to front corner of wall relative to pics
            #

            self.fiducials = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:fiducial-points",
                    project=self.test_project.id,
                    spatial_frame=models.SpatialFrame(
                        parent_frame=self.toolpath.id,
                        transform={"translation_xyz": {"x": 1010, "y": 1000, "z": 10}},
                    ),
                )
            )

            self.specimen_bbox = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:document:bounding-box",
                    project=self.test_project.id,
                    local_data={
                        "min": {"x": -10, "y": 50, "z": 50},
                        "max": {"x": 0, "y": 60, "z": 60},
                    },
                    spatial_frame=models.SpatialFrame(
                        parent_frame=self.fiducials.id, transform={}
                    ),
                )
            )

            #
            # Fiducial coordinates moved and rotated to *front* corner of wall
            # relative to pics with z into wall and x along wall
            #

            self.fiducials_rot = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:fiducial-points",
                    project=self.test_project.id,
                    spatial_frame=models.SpatialFrame(
                        parent_frame=self.toolpath.id,
                        transform={
                            "translation_xyz": {"x": 1010, "y": 1000, "z": 10},
                            "rotation_euler_abg": {
                                "a": numpy.pi / 2.0,  # Z
                                "b": 0,  # Y
                                "g": 0,  # X
                            },
                        },
                    ),
                )
            )

            self.specimen_bbox_rot = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:document:bounding-box",
                    project=self.test_project.id,
                    local_data={
                        "min": {"x": 50, "y": 0, "z": 50},
                        "max": {"x": 60, "y": 10, "z": 60},
                    },
                    spatial_frame=models.SpatialFrame(
                        parent_frame=self.fiducials_rot.id, transform={}
                    ),
                )
            )

            #
            # Fiducial coordinates moved and rotated to *front* corner of wall
            # relative to pics with y now vertical and z toward the camera
            #

            self.fiducials_rot2 = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:fiducial-points",
                    project=self.test_project.id,
                    spatial_frame=models.SpatialFrame(
                        parent_frame=self.toolpath.id,
                        transform={
                            "translation_xyz": {"x": 1010, "y": 1000, "z": 10},
                            "rotation_euler_abg": {
                                "a": numpy.pi / 2.0,  # Z
                                "b": 0,  # Y
                                "g": numpy.pi / 2.0,  # X
                            },
                        },
                    ),
                )
            )

            self.specimen_bbox_rot2 = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:document:bounding-box",
                    project=self.test_project.id,
                    local_data={
                        "min": {"x": 50, "y": 50, "z": -10},
                        "max": {"x": 60, "y": 60, "z": 0},
                    },
                    spatial_frame=models.SpatialFrame(
                        parent_frame=self.fiducials_rot2.id, transform={}
                    ),
                )
            )

            #
            # Fiducial coordinates moved and rotated to *front* corner of wall
            # relative to pics with y negative along wall, x vertical, and z toward the camera
            #

            self.fiducials_rot3 = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:fiducial-points",
                    project=self.test_project.id,
                    spatial_frame=models.SpatialFrame(
                        parent_frame=self.toolpath.id,
                        transform={
                            "translation_xyz": {"x": 1010, "y": 1000, "z": 10},
                            "rotation_euler_abg": {
                                "a": numpy.pi / 2.0,  # Z
                                "b": -numpy.pi / 2.0,  # Y
                                "g": numpy.pi / 2.0,  # X
                            },
                        },
                    ),
                )
            )

            self.specimen_bbox_rot3 = artifact_repo.create(
                models.DigitalArtifact(
                    type_urn="urn:x-mfg:artifact:digital:document:bounding-box",
                    project=self.test_project.id,
                    local_data={
                        "min": {"x": 50, "y": -60, "z": -10},
                        "max": {"x": 60, "y": -50, "z": 0},
                    },
                    spatial_frame=models.SpatialFrame(
                        parent_frame=self.fiducials_rot3.id, transform={}
                    ),
                )
            )


def to_list(bbox_artifact_dict, rounded=False):
    def maybe_round(num):
        return num if not rounded else round(num)

    return numpy.array(
        [
            [
                maybe_round(bbox_artifact_dict.get("min", {}).get("x", 0)),
                maybe_round(bbox_artifact_dict.get("min", {}).get("y", 0)),
                maybe_round(bbox_artifact_dict.get("min", {}).get("z", 0)),
            ],
            [
                maybe_round(bbox_artifact_dict.get("max", {}).get("x", 0)),
                maybe_round(bbox_artifact_dict.get("max", {}).get("y", 0)),
                maybe_round(bbox_artifact_dict.get("max", {}).get("z", 0)),
            ],
        ],
        dtype=int,
    ).tolist()


def test_basic_bbox_into_frame(storage_layer, test_project):
    """
    Test bounding box into frame transform
    """

    artifacts = TestFrameRelatedArtifacts(storage_layer, test_project)

    with ServiceLayerContext(storage_layer) as service_layer:
        bbox_services: BoundingBoxServices = service_layer.artifact_services_for(
            artifacts.specimen_bbox, BoundingBoxServices
        )

        transformed_bbox = to_list(
            bbox_services.transform_artifact_bbox_into_frame(
                artifacts.specimen_bbox, artifacts.toolpath.id
            )
        )

        assert transformed_bbox == [[1000, 1050, 60], [1010, 1060, 70]]

        #
        # Equivalent BBoxes from rotated frames
        #

        assert transformed_bbox == to_list(
            bbox_services.transform_artifact_bbox_into_frame(
                artifacts.specimen_bbox_rot, artifacts.toolpath.id
            )
        )

        assert transformed_bbox == to_list(
            bbox_services.transform_artifact_bbox_into_frame(
                artifacts.specimen_bbox_rot2, artifacts.toolpath.id
            ),
        )

        assert transformed_bbox == to_list(
            bbox_services.transform_artifact_bbox_into_frame(
                artifacts.specimen_bbox_rot3, artifacts.toolpath.id
            ),
        )


def test_bbox_into_frame_upstream(storage_layer, test_project):
    """
    Test bounding box into frame transform with exactly-reversed transform in the chain
    """

    artifacts = TestFrameRelatedArtifacts(storage_layer, test_project)

    with ServiceLayerContext(storage_layer) as service_layer:
        bbox_services: BoundingBoxServices = service_layer.artifact_services_for(
            artifacts.specimen_bbox, BoundingBoxServices
        )

        original_bbox = to_list(artifacts.specimen_bbox_rot2.local_data)

        transformed_bbox = to_list(
            bbox_services.transform_artifact_bbox_into_frame(
                artifacts.specimen_bbox, artifacts.thermal_cloud.id
            ),
            rounded=True,
        )

        assert original_bbox == transformed_bbox
