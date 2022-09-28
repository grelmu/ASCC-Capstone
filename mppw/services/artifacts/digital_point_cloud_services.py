import furl
import pydantic
from typing import List, Optional, Any

from .. import ArtifactServices
from ... import models


class UnknownPointCloudTypeException(Exception):
    pass


class UnknownPointCloudStorageStrategyException(Exception):
    pass


class XyztPoint(models.BaseJsonModel):
    p: List
    ctx: Optional[Any]


class PointCloudServices(ArtifactServices):
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

    class DbVoxMeta(pydantic.BaseModel):
        max_scale: int
        base_units: Optional[str]
        address_field: Optional[str] = "vaddr"
        dt_field: Optional[str] = "stamp"
        storage_strategy: str
        storage_strategy_params: Any

    class XyzFieldsParams(pydantic.BaseModel):
        x_field: str = "x"
        y_field: str = "y"
        z_field: str = "z"

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
