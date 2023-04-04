import furl
import pydantic
from typing import List, Optional, Any
import dbvox
import json_stream
import json_stream.base
import arrow

from .. import ArtifactServices
from .. import OperationServices
from ... import models


class UnknownPointCloudTypeException(Exception):
    pass


class UnknownPointCloudStorageStrategyException(Exception):
    pass


class XyztPoint(models.BaseJsonModel):

    """
    A point in space and time

    Consists of a "p" list of length 4, xyzt coordinates, and an
    (optional) "ctx" (context) object with any additional metadata.

    The xyz coordinates are numeric, and the time coordinate is
    specified as a format-native datetime.  In JSON this is an
    ISO datetime string but other formats may be supported.
    """

    p: List
    ctx: Optional[Any]


class PointCloudServices(ArtifactServices):
    class DbVoxMeta(pydantic.BaseModel):
        max_scale: int
        base_units: Optional[str]
        address_field: Optional[str] = "vaddr"
        dt_field: Optional[str] = "stamp"
        storage_strategy: str
        storage_strategy_params: Any
        xyzt_bounds: Any

        @pydantic.validator("xyzt_bounds")
        def validate_xyzt_bounds(cls, v):
            if not v:
                return None
            v = list(list(mm) for mm in v)
            for i in [0, 1]:
                v[i][3] = arrow.get(v[i][3]).to("utc").datetime
            return v

    class XyzFieldsParams(pydantic.BaseModel):
        x_field: str = "x"
        y_field: str = "y"
        z_field: str = "z"

    def init(self, artifact: models.DigitalArtifact, **kwargs):

        if not artifact.url_data:

            parent: models.Operation = self.operation_parent(artifact)
            if parent is None:
                raise Exception(
                    "Cannot initialize point cloud, no parent operation found for storage"
                )

            for process_data_node in parent.attachments.find_nodes_by_path(
                OperationServices.PROCESS_DATA_KIND_PATH
            ):
                process_data_node: models.AttachmentGraph.AttachmentNode

                process_data_artifact: models.Artifact = (
                    self.repo_layer.artifacts.query_one(
                        id=process_data_node.artifact_id
                    )
                )
                if not isinstance(process_data_artifact, models.DigitalArtifact):
                    continue

                process_data_scheme = furl.furl(process_data_artifact.url_data).scheme

                if process_data_scheme in ["mongodb"]:
                    return self._init_mongodb_dbvox(
                        artifact, process_data_artifact.url_data, **kwargs
                    )

            raise Exception(
                "Cannot initialize point cloud, no compatible operation process data found for storage"
            )

        return artifact

    def _init_mongodb_dbvox(
        self,
        artifact: models.DigitalArtifact,
        mongodb_url: str,
        **kwargs,
    ):

        artifact.url_data = self._build_default_mongodb_dbvox_url(artifact, mongodb_url)
        self._ensure_mongodb_dbvox_meta(artifact)
        self._ensure_mongodb_dbvox_indices(artifact)
        self.repo_layer.artifacts.update(artifact)
        return artifact

    def _build_default_mongodb_dbvox_url(
        self, artifact: models.DigitalArtifact, mongodb_url: str
    ):
        artifact_furl = furl.furl(mongodb_url)
        artifact_furl.scheme = "mongodb+dbvox"
        artifact_furl.path.segments.append(f"_artcoll-{str(artifact.id)}")
        return artifact_furl.url

    def _get_mongodb_dbvox_collection(self, dbvox_url: str):

        import pymongo

        dbvox_furl = furl.furl(dbvox_url)
        base_furl = furl.furl(dbvox_url)

        base_furl.scheme = "mongodb"
        base_furl.path = base_furl.path.segments[0]

        base_url = self.repo_layer.storage_layer.resolve_local_storage_url_host(
            base_furl.url
        )

        client = pymongo.MongoClient(base_url)
        return client[dbvox_furl.path.segments[0]][dbvox_furl.path.segments[1]]

    def _get_mongodb_dbvox_collection_and_meta(self, dbvox_url: str):

        import pymongo.collection

        dbvox_collection: pymongo.collection.Collection = (
            self._get_mongodb_dbvox_collection(dbvox_url)
        )
        meta = dbvox_collection.find_one({"_id": None})
        if meta is not None:
            meta = PointCloudServices.DbVoxMeta(**meta)

        return (dbvox_collection, meta)

    def _ensure_mongodb_dbvox_meta(
        self,
        artifact: models.DigitalArtifact,
    ):
        import pymongo
        import pymongo.errors
        import pymongo.collection

        dbvox_collection: pymongo.collection.Collection = (
            self._get_mongodb_dbvox_collection(artifact.url_data)
        )
        default_meta = PointCloudServices.DbVoxMeta(
            max_scale=21, storage_strategy="xyz_fields"
        )
        default_meta_dict = default_meta.dict()
        default_meta_dict.update({"_id": None})

        try:
            dbvox_collection.insert_one(default_meta_dict)
            return True
        except pymongo.errors.DuplicateKeyError:
            return False

    def _ensure_mongodb_dbvox_indices(
        self,
        artifact: models.DigitalArtifact,
    ):
        import pymongo
        import pymongo.errors
        import pymongo.collection

        dbvox_collection, meta = self._get_mongodb_dbvox_collection_and_meta(
            artifact.url_data
        )

        dbvox_collection: pymongo.collection.Collection
        meta: PointCloudServices.DbVoxMeta

        if meta.storage_strategy == "xyz_fields":

            dbvox_collection.create_index(
                [
                    (meta.dt_field, pymongo.ASCENDING),
                ]
            )

            dbvox_collection.create_index(
                [
                    (meta.address_field, pymongo.ASCENDING),
                    (meta.dt_field, pymongo.ASCENDING),
                ]
            )

        else:
            raise UnknownPointCloudStorageStrategyException(
                f"Unknown storage strategy {meta.storage_strategy} for point cloud {artifact.id} at {artifact.url_data}"
            )

    def insert(self, cloud_artifact: models.DigitalArtifact, json_gen, **kwargs):

        if not cloud_artifact.url_data:
            raise UnknownPointCloudTypeException("No URL found for point cloud.")

        cloud_furl = furl.furl(cloud_artifact.url_data)
        if cloud_furl.scheme == "mongodb+dbvox":
            return self._insert_mongodb_dbvox(cloud_artifact, json_gen, **kwargs)
        else:
            raise UnknownPointCloudTypeException(
                f"Unknown point cloud type for {cloud_furl.url}"
            )

    def _insert_mongodb_dbvox(
        self, cloud_artifact: models.DigitalArtifact, json_gen, max_batch_size=1000
    ):

        import pymongo.collection

        dbvox_collection, meta = self._get_mongodb_dbvox_collection_and_meta(
            cloud_artifact.url_data
        )

        dbvox_collection: pymongo.collection.Collection
        meta: PointCloudServices.DbVoxMeta
        space = dbvox.Vox3Space(meta.max_scale)

        if meta.storage_strategy == "xyz_fields":

            params = PointCloudServices.XyzFieldsParams(
                **(meta.storage_strategy_params or {})
            )

            next_batch = []

            def write_batch():

                # Strictly write bounds in UTC datetime
                for i in [0, 1]:
                    meta.xyzt_bounds[i][3] = (
                        arrow.get(meta.xyzt_bounds[i][3]).to("utc").datetime
                    )

                dbvox_collection.update_one(
                    {"_id": None}, {"$set": {"xyzt_bounds": meta.xyzt_bounds}}
                )
                dbvox_collection.insert_many(next_batch)
                next_batch.clear()

            for point_doc in (
                PointCloudServices._stream_json_to_value(p)
                for p in json_stream.load(json_gen)
            ):

                point_doc.setdefault("ctx", {})
                # Strictly write points in UTC datetime
                point_doc["p"][3] = arrow.get(point_doc["p"][3]).to("utc").datetime
                xyzt_point = XyztPoint(**point_doc)
                xyzt_point.ctx.update(
                    {
                        params.x_field: xyzt_point.p[0],
                        params.y_field: xyzt_point.p[1],
                        params.z_field: xyzt_point.p[2],
                        meta.dt_field: xyzt_point.p[3],
                        meta.address_field: space.get_vox(*xyzt_point.p[0:3]).to_addr(),
                    }
                )

                next_batch.append(xyzt_point.ctx)
                meta.xyzt_bounds = PointCloudServices._update_bounds(
                    meta.xyzt_bounds, xyzt_point.p
                )

                if (
                    max_batch_size not in [None, 0]
                    and len(next_batch) >= max_batch_size
                ):
                    write_batch()

            if next_batch:
                write_batch()

        else:
            raise UnknownPointCloudStorageStrategyException(
                f"Unknown storage strategy {meta.storage_strategy} for point cloud {cloud_artifact.id} at {cloud_artifact.url_data}"
            )

    def sample(self, cloud_artifact: models.DigitalArtifact, space_bounds, time_bounds):

        if not cloud_artifact.url_data:
            raise UnknownPointCloudTypeException("No URL found for point cloud.")

        cloud_furl = furl.furl(cloud_artifact.url_data)
        if cloud_furl.scheme == "mongodb+dbvox":
            return self.sample_mongodb_dbvox(cloud_furl.url, space_bounds, time_bounds)
        else:
            raise UnknownPointCloudTypeException(
                f"Unknown point cloud type for {cloud_furl.url}"
            )

    @staticmethod
    def in_space_bounds(xyz, space_bounds):
        return (
            space_bounds[0][0] <= xyz[0]
            and xyz[0] < space_bounds[1][0]
            and space_bounds[0][1] <= xyz[1]
            and xyz[1] < space_bounds[1][1]
            and space_bounds[0][2] <= xyz[2]
            and xyz[2] < space_bounds[1][2]
        )

    @staticmethod
    def _stream_json_to_value(maybe_value):
        if isinstance(maybe_value, json_stream.base.StreamingJSONObject):
            return dict(
                (k, PointCloudServices._stream_json_to_value(v))
                for k, v in maybe_value.items()
            )
        elif isinstance(maybe_value, json_stream.base.StreamingJSONList):
            return list(
                PointCloudServices._stream_json_to_value(v) for v in maybe_value
            )
        return maybe_value

    @staticmethod
    def _update_bounds(bounds, xyzt):
        if bounds is None:
            return [list(xyzt), list(xyzt)]
        for i in range(0, 4):
            if bounds[0][i] > xyzt[i]:
                bounds[0][i] = xyzt[i]
            if bounds[1][i] < xyzt[i]:
                bounds[1][i] = xyzt[i]
        return bounds

    @staticmethod
    def in_spacetime_bounds(xyzt, space_bounds, time_bounds):
        return PointCloudServices.in_space_bounds(xyzt, space_bounds) and (
            time_bounds is None
            or (time_bounds[0] <= xyzt[3] and xyzt[3] < time_bounds[1])
        )

    @staticmethod
    def mdb_vox_time_query(voxel, vaddr_field, time_bounds, dt_field):
        query = {vaddr_field: {"$regex": "^" + voxel.to_addr()}}
        if time_bounds is not None:
            query[dt_field] = {"$gte": time_bounds[0], "$lt": time_bounds[1]}
        return query

    def get_bounds(self, cloud_artifact: models.DigitalArtifact):

        if not cloud_artifact.url_data:
            raise UnknownPointCloudTypeException("No URL found for point cloud.")

        cloud_furl = furl.furl(cloud_artifact.url_data)
        if cloud_furl.scheme != "mongodb+dbvox":
            raise UnknownPointCloudTypeException(
                f"Unknown point cloud type for {cloud_furl.url}"
            )

        else:
            import pymongo

            dbvox_furl = furl.furl(cloud_furl.url)
            base_furl = furl.furl(dbvox_furl)
            base_furl.scheme = "mongodb"
            base_furl.path = base_furl.path.segments[0]

            base_url = self.repo_layer.storage_layer.resolve_local_storage_url_host(
                base_furl.url
            )

            client = pymongo.MongoClient(base_url)
            collection = client[dbvox_furl.path.segments[0]][
                dbvox_furl.path.segments[1]
            ]

            meta = collection.find_one({"_id": None})
            return meta["xyzt_bounds"]

    def sample_mongodb_dbvox(self, dbvox_url, space_bounds, time_bounds):

        import pymongo
        import dbvox

        dbvox_furl = furl.furl(dbvox_url)
        base_furl = furl.furl(dbvox_furl)
        base_furl.scheme = "mongodb"
        base_furl.path = base_furl.path.segments[0]

        base_url = self.repo_layer.storage_layer.resolve_local_storage_url_host(
            base_furl.url
        )

        client = pymongo.MongoClient(base_url)
        collection = client[dbvox_furl.path.segments[0]][dbvox_furl.path.segments[1]]

        meta = PointCloudServices.DbVoxMeta(**(collection.find_one({"_id": None})))
        space = dbvox.Vox3Space(meta.max_scale)
        voxels = space.get_cover(*(tuple(zip(*space_bounds))))
        # Strictly query points in UTC datetime
        time_bounds = (
            [arrow.get(dt).to("utc").datetime for dt in time_bounds]
            if time_bounds is not None
            else None
        )

        vox_query = {
            "$or": [
                PointCloudServices.mdb_vox_time_query(
                    voxel, meta.address_field, time_bounds, meta.dt_field
                )
                for voxel in voxels
            ]
        }

        cursor = collection.find(vox_query)

        if meta.storage_strategy == "xyz_fields":
            params = PointCloudServices.XyzFieldsParams(
                **(meta.storage_strategy_params or {})
            )
            for doc in cursor:
                xyzt = [
                    doc[params.x_field],
                    doc[params.y_field],
                    doc[params.z_field],
                    doc[meta.dt_field],
                ]
                if PointCloudServices.in_space_bounds(xyzt, space_bounds):
                    yield XyztPoint(p=xyzt, ctx=doc)

        else:
            raise UnknownPointCloudStorageStrategyException(
                f"Unknown storage strategy {meta.storage_strategy} for point cloud {dbvox_url}"
            )
