import open3d
import numpy
from .. import ArtifactServices

from ... import models
from .. import provenance_services

"""
TODO: Refactor and add support for meshes
"""


class BoundingBoxServices(ArtifactServices):

    """
    Services related to bounding box artifacts
    """

    # Open3D doesn't have a named constant for this
    OPEN3D_GEOMETRY_TYPE_ORIENTED_BOUNDING_BOX_VALUE = 11

    def transform_artifact_bbox_into_frame(
        self,
        geometry_artifact: models.DigitalArtifact,
        frame_artifact_id,
    ):
        """
        Given an artifact bounding box, transform the bounds into the frame
        of another artifact.

        Works by finding a path between artifacts and then transforming the (oriented)
        box frame-by-frame until reaching the target frame.  Produces another axis-aligned
        bounding box.
        """

        geometry_3d = self.artifact_to_geometry_3d(geometry_artifact)

        provenance_services = self.service_layer.provenance_services()
        frame_path = provenance_services.build_artifact_frame_path(
            geometry_artifact.id,
            frame_artifact_id,
        )

        if frame_path is None:
            return None

        transforms_h3d = self.frame_path_to_transforms_h3d(frame_path)
        bbox_3d: open3d.geometry.OrientedBoundingBox = (
            geometry_3d.get_oriented_bounding_box()
        )

        return self.geometry_3d_to_artifact_bbox(
            self.transform_geometry_3d(bbox_3d, transforms_h3d)
        )

    def transform_geometry_3d(self, geometry_3d, transforms_h3d):
        """
        Given a 3d geometry and a number of (homogenous) 3d transforms, transforms
        the geometry via each transform in-order.
        """

        is_bbox = (
            geometry_3d.get_geometry_type().value
            == BoundingBoxServices.OPEN3D_GEOMETRY_TYPE_ORIENTED_BOUNDING_BOX_VALUE
        )

        # DRAGONS: BBoxes can't currently be transformed this way for reasons in O3D,
        # so transform an equivalent point cloud instead.
        if is_bbox:
            geometry_3d = open3d.geometry.PointCloud(geometry_3d.get_box_points())

        for transform_h3d in transforms_h3d:
            geometry3d = geometry_3d.transform(transform_h3d)

        if is_bbox:
            geometry_3d = geometry_3d.get_oriented_bounding_box()

        return geometry_3d

    def frame_path_to_transforms_h3d(
        self, frame_path: provenance_services.ArtifactFramePath
    ):
        """
        Convert a frame path from an artifact frame graph into a set
        of transforms.

        Converting to an artifact child vs parent inverts the transform.
        """

        transforms_h3d = []
        for path_node, (from_node, to_node, data) in zip(
            frame_path.path_nodes, frame_path.path_edges
        ):
            frame: models.SpatialFrame = data["frame"]

            rotation = open3d.geometry.get_rotation_matrix_from_zyx(
                numpy.array(
                    [
                        frame.transform.get("rotation_euler_abg", {}).get("a", 0),
                        frame.transform.get("rotation_euler_abg", {}).get("b", 0),
                        frame.transform.get("rotation_euler_abg", {}).get("g", 0),
                    ],
                    dtype=numpy.float64,
                )
            )

            translation = numpy.array(
                [
                    frame.transform.get("translation_xyz", {}).get("x", 0),
                    frame.transform.get("translation_xyz", {}).get("y", 0),
                    frame.transform.get("translation_xyz", {}).get("z", 0),
                ],
                dtype=numpy.float64,
            )

            if path_node != to_node:
                # Invert parent frame transform if we're working *forwards*
                # i.e. the child frame is the target vs the parent frame
                rotation = numpy.transpose(rotation)
                translation = numpy.matmul(rotation, translation) * -1.0

            transform_h3d = numpy.eye(4)
            transform_h3d[:3, :3] = rotation
            transform_h3d[:3, 3] = translation

            transforms_h3d.append(transform_h3d)

        return transforms_h3d

    def artifact_to_geometry_3d(self, artifact: models.DigitalArtifact):
        """
        Convert a digital artifact into an (open)3D geometry
        """

        if artifact.type_urn in ["urn:x-mfg:artifact:digital:document:bounding-box"]:
            return open3d.geometry.AxisAlignedBoundingBox(
                numpy.array(
                    [
                        artifact.local_data["min"]["x"],
                        artifact.local_data["min"]["y"],
                        artifact.local_data["min"]["z"],
                    ],
                    dtype=numpy.float64,
                ),
                numpy.array(
                    [
                        artifact.local_data["max"]["x"],
                        artifact.local_data["max"]["y"],
                        artifact.local_data["max"]["z"],
                    ],
                    dtype=numpy.float64,
                ),
            )
        else:
            raise NotImplementedError(
                f"Cannot create geometry from artifact {artifact.id} of type {artifact.type_urn}"
            )

    def geometry_3d_to_artifact_bbox(self, geometry_3d: open3d.geometry.Geometry3D):
        """
        Convert an (open)3D geometry into an artifact bounding box schema
        """

        aabb_3d: open3d.geometry.AxisAlignedBoundingBox = (
            geometry_3d.get_axis_aligned_bounding_box()
        )

        min_bound = aabb_3d.get_min_bound()
        max_bound = aabb_3d.get_max_bound()

        return {
            "min": dict(zip(["x", "y", "z"], list(min_bound))),
            "max": dict(zip(["x", "y", "z"], list(max_bound))),
        }
