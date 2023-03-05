import fastapi
from fastapi import Security, Depends
import starlette.background
import typing
from typing import Union, List
import pydantic
import json
import arrow
import os
import shutil
import tempfile
import asyncio
import math

from mppw import logger
from . import models
from . import repositories
from .repositories import request_repo_layer
from . import security
from .security import (
    request_user,
    READ_PROVENANCE_SCOPE,
    MODIFY_PROVENANCE_SCOPE,
    MODIFY_ARTIFACT_SCOPE,
)
from . import project_endpoints
from . import services
from .services import request_service_layer
from . import endpoints


def create_router(app):

    router = fastapi.APIRouter(prefix="/api/artifacts")

    #
    # CRUD
    #

    @router.post(
        "/",
        response_model=models.AnyArtifact,
        status_code=fastapi.status.HTTP_201_CREATED,
    )
    def create(
        artifact: models.AnyArtifact,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[MODIFY_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        project_endpoints.check_project_claims_for_user(user, [str(artifact.project)])

        art_repo = repo_layer.artifacts
        return art_repo.create(artifact)

    @router.get("/{id}", response_model=models.AnyArtifact)
    def read(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        result = repo_layer.artifacts.query_one(
            id=id, project_ids=project_endpoints.project_claims_for_user(user)
        )

        if result is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return result

    @router.get("/", response_model=List[models.AnyArtifact])
    def query(
        project_ids: List[str] = fastapi.Query(None),
        name: str = fastapi.Query(None),
        tags: List[str] = fastapi.Query(None),
        active: bool = fastapi.Query(True),
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        if project_ids is None:
            project_ids = project_endpoints.project_claims_for_user(user)

        project_endpoints.check_project_claims_for_user(user, project_ids)

        return list(
            repo_layer.artifacts.query(
                project_ids=project_ids,
                name=name,
                tags=tags,
                active=active,
            )
        )

    class PaginatedArtifacts(models.BaseJsonModel):
        results: List[models.Artifact]
        total: int

    @router.get("/paged/", response_model=PaginatedArtifacts)
    def paged_query(
        project_ids: List[str] = fastapi.Query(None),
        name: str = fastapi.Query(None),
        tags: List[str] = fastapi.Query(None),
        active: bool = fastapi.Query(True),
        page_size: int = fastapi.Query(None),
        page_num: int = fastapi.Query(None),
        sort_col: str = fastapi.Query(None),
        sort_dir: str = fastapi.Query(None),
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        if project_ids is None:
            project_ids = project_endpoints.project_claims_for_user(user)

        project_endpoints.check_project_claims_for_user(user, project_ids)

        # Calculate the skip value based on page_size and page_num args
        skip = page_size * (page_num - 1) if None not in (page_size, page_num) else None

        # MongoDB's sort function expects either 1 or -1
        #   Convert sort_dir to match
        if sort_dir is not None:
            sort_dir = 1 if sort_dir == "asc" else -1

        results, total = repo_layer.artifacts.paged_query(
            project_ids=project_ids,
            name=name,
            tags=tags,
            active=active,
            skip=skip,
            limit=page_size,
            sort_col=sort_col,
            sort_dir=sort_dir,
        )

        return PaginatedArtifacts(results=list(results), total=total)

    @router.put("/{id}", response_model=bool)
    def update(
        id: str,
        artifact: models.AnyArtifact,
        current_user: models.User = Security(
            request_user(app), scopes=[MODIFY_ARTIFACT_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        if id != str(artifact.id):
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST)

        modified = repo_layer.artifacts.update(
            artifact,
            project_ids=project_endpoints.project_claims_for_user(current_user),
        )

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.patch("/{id}", response_model=bool)
    def patch(
        id: str,
        changes: List[endpoints.Change],
        current_user: models.User = Security(
            request_user(app), scopes=[MODIFY_ARTIFACT_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):
        def update_fn(artifact: models.DigitalArtifact):

            for change in changes:
                if change.op == "replace":
                    setattr(artifact, change.path, change.value)
                elif change.op == "remove":
                    setattr(artifact, change.path, None)

            return artifact

        modified = repo_layer.artifacts.partial_update(
            id,
            update_fn,
            project_ids=project_endpoints.project_claims_for_user(current_user),
        )

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.delete("/{id}", response_model=bool)
    def delete(
        id: str,
        preserve_data: bool = True,
        current_user: models.User = Security(
            request_user(app), scopes=[MODIFY_PROVENANCE_SCOPE]
        ),
        repo_layer=Depends(request_repo_layer(app)),
    ):

        modified = (
            repo_layer.artifacts.deactivate
            if preserve_data
            else repo_layer.artifacts.delete
        )(id, project_ids=project_endpoints.project_claims_for_user(current_user))

        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    #
    # Services
    #

    @router.post("/{id}/services/artifact/init", response_model=models.AnyArtifact)
    def init(
        id: str,
        args: dict = {},
        user: models.User = Security(request_user(app), scopes=[MODIFY_ARTIFACT_SCOPE]),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        artifact: models.Artifact = read(id, user, service_layer.repo_layer)
        services = service_layer.artifact_services_for(artifact)
        return services.init(artifact, **args)

    @router.get("/{id}/services/artifact/parent", response_model=models.Operation)
    def parent(
        id: str,
        user: models.User = Security(request_user(app), scopes=[READ_PROVENANCE_SCOPE]),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):
        artifact: models.Artifact = read(id, user, service_layer.repo_layer)
        services = service_layer.artifact_services_for(artifact)
        return services.operation_parent(artifact)

    #
    # Schema
    #

    @router.get(
        "/{id}/services/artifact/schema",
        response_model=services.ResolvedSchema,
    )
    def get_schema(
        id: str,
        user: models.User = Security(request_user(app), scopes=[READ_PROVENANCE_SCOPE]),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):
        artifact: models.Artifact = read(id, user, service_layer.repo_layer)

        schema = service_layer.schema_services().query_resolved_project_schema(
            artifact.project,
            type_urns=[artifact.type_urn],
            active=True,
            current=True,
        )

        if not schema:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return schema

    @router.get(
        "/{id}/services/artifact/digital/json_schema",
        response_model=typing.Optional[dict],
    )
    def json_schema(
        id: str,
        user: models.User = Security(request_user(app), scopes=[READ_PROVENANCE_SCOPE]),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):
        schema: services.ResolvedSchema = get_schema(id, user, service_layer)

        return schema.schema_model.json_schema

    #
    # Provenance
    #

    @router.get(
        "/{id}/services/artifact/provenance",
        response_model=endpoints.ProvenanceGraphModel,
    )
    def get_provenance(
        id: str,
        strategy: str = None,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        artifact: models.Artifact = read(id, user, service_layer.repo_layer)
        services = service_layer.provenance_services()
        return endpoints.ProvenanceGraphModel.from_graph(
            services.build_artifact_provenance(artifact.id, strategy=strategy)
        )

    @router.get(
        "/{id}/services/artifact/frame_graph",
        response_model=endpoints.ArtifactFrameGraphModel,
    )
    def get_frame_graph(
        id: str,
        strategy: str = None,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        artifact: models.Artifact = read(id, user, service_layer.repo_layer)
        services = service_layer.provenance_services()
        return endpoints.ArtifactFrameGraphModel.from_graph(
            services.build_artifact_frame_graph(artifact.id, strategy=strategy)
        )

    @router.get(
        "/{id}/services/artifact/frame_path",
        response_model=typing.Optional[endpoints.ArtifactFramePathModel],
    )
    def get_frame_path(
        id: str,
        to_id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        artifact: models.Artifact = read(id, user, service_layer.repo_layer)
        services = service_layer.provenance_services()
        return endpoints.ArtifactFramePathModel.from_path(
            services.build_artifact_frame_path(artifact.id, to_id)
        )

    from .services.artifacts.digital_file_services import FileServices

    @router.get(
        "/{id}/services/file/download",
    )
    def file_download(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        artifact: models.DigitalArtifact = read(id, user, service_layer.repo_layer)
        service: FileServices = service_layer.artifact_services_for(
            artifact, FileServices
        )

        if not service.can_download(artifact):
            return fastapi.responses.RedirectResponse(artifact.url_data)

        meta, data = service.download(artifact)

        if data is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return fastapi.responses.StreamingResponse(data, media_type=meta.content_type)

    from .services.artifacts.digital_file_bucket_services import FileBucketServices

    @router.get(
        "/{id}/services/file-bucket/download",
    )
    def file_bucket_download(
        id: str,
        path: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        artifact: models.DigitalArtifact = read(id, user, service_layer.repo_layer)
        service: FileBucketServices = service_layer.artifact_services_for(
            artifact, FileBucketServices
        )

        meta, data = service.download(artifact, path)

        if data is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return fastapi.responses.StreamingResponse(data, media_type=meta.content_type)

    class SyncUploadFile:
        def __init__(self, uf: fastapi.UploadFile):
            self.uf = uf

        def write(self, data: typing.Union[bytes, str]) -> None:
            return asyncio.run(self.uf.write(data))

        def read(self, size: int = -1) -> typing.Union[bytes, str]:
            return asyncio.run(self.uf.read(size))

        async def seek(self, offset: int) -> None:
            return asyncio.run(self.uf.seek(offset))

        async def close(self) -> None:
            return asyncio.run(self.uf.close())

    @router.post(
        "/{id}/services/file-bucket/upload",
        response_model=str,
        status_code=fastapi.status.HTTP_201_CREATED,
    )
    def file_bucket_upload(
        id: str,
        path: str = fastapi.Body(None),
        file: fastapi.UploadFile = fastapi.File(None),
        replace: bool = fastapi.Body(None),
        user: security.ScopedUser = Security(
            request_user(app), scopes=[MODIFY_ARTIFACT_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        if path is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        artifact: models.DigitalArtifact = read(id, user, service_layer.repo_layer)
        service: FileBucketServices = service_layer.artifact_services_for(
            artifact, FileBucketServices
        )

        return service.upload(artifact, path, SyncUploadFile(file), replace=replace)

    @router.post(
        "/{id}/services/file-bucket/ls", response_model=List[repositories.BucketFile]
    )
    def file_bucket_ls(
        id: str,
        path: str = None,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        artifact: models.DigitalArtifact = read(id, user, service_layer.repo_layer)
        service: FileBucketServices = service_layer.artifact_services_for(
            artifact, FileBucketServices
        )

        return list(service.ls(artifact, path))

    @router.get(
        "/{id}/services/database-bucket/stats",
        response_model=repositories.DatabaseBucketStats,
    )
    def database_bucket(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        artifact: models.Artifact = read(id, user, service_layer.repo_layer)

        service: services.DatabaseBucketServices = service_layer.artifact_services_for(
            artifact
        )
        return service.stats(artifact)

    class RenamePaths(pydantic.BaseModel):
        path: str
        new_path: str

    @router.post("/{id}/services/file-bucket/rename", response_model=bool)
    def file_bucket_rename(
        id: str,
        rename_paths: RenamePaths,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[MODIFY_ARTIFACT_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        artifact: models.DigitalArtifact = read(id, user, service_layer.repo_layer)
        service: FileBucketServices = service_layer.artifact_services_for(
            artifact, FileBucketServices
        )

        if not service.rename(artifact, rename_paths.path, rename_paths.new_path):
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.post("/{id}/services/file-bucket/delete", response_model=bool)
    def file_bucket_delete(
        id: str,
        path: str = fastapi.Body(None),
        user: security.ScopedUser = Security(
            request_user(app), scopes=[MODIFY_ARTIFACT_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        if path is None:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        artifact: models.DigitalArtifact = read(id, user, service_layer.repo_layer)
        service: FileBucketServices = service_layer.artifact_services_for(
            artifact, FileBucketServices
        )

        if not service.delete(artifact, path):
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    from .services.artifacts.digital_point_cloud_services import (
        PointCloudServices,
        XyztPoint,
    )

    @router.post("/{id}/services/point-cloud/insert", response_model=bool)
    def point_cloud_insert(
        id: str,
        body_stream=fastapi.Depends(endpoints.sync_body_stream),
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):
        artifact: models.Artifact = read(id, user, service_layer.repo_layer)
        services: PointCloudServices = service_layer.artifact_services_for(
            artifact, PointCloudServices
        )

        services.insert(artifact, body_stream)
        return True

    @router.get("/{id}/services/point-cloud/points", response_model=List[XyztPoint])
    def point_cloud_points(
        id: str,
        space_bounds: str,
        time_bounds: str = None,
        coerce_dt_bounds: bool = False,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):
        space_bounds = json.loads(space_bounds)
        time_bounds = json.loads(time_bounds) if time_bounds else None
        if time_bounds and coerce_dt_bounds:
            time_bounds = tuple(arrow.get(bound).datetime for bound in time_bounds)

        artifact: models.Artifact = read(id, user, service_layer.repo_layer)
        services: PointCloudServices = service_layer.artifact_services_for(
            artifact, PointCloudServices
        )

        point_cursor = services.sample(artifact, space_bounds, time_bounds)
        return endpoints.StreamingJsonResponse(point_cursor)

    @router.get("/{id}/services/point-cloud/bounds")
    def point_cloud_bounds(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        artifact: models.Artifact = read(id, user, service_layer.repo_layer)

        meta = service_layer.artifact_services_for(
            artifact, PointCloudServices
        ).get_bounds(artifact)

        return meta

    @router.get("/{id}/services/point-cloud/cloudfile")
    def point_cloud_cloudfile(
        id: str,
        space_bounds: str,
        time_bounds: str = None,
        coerce_dt_bounds: bool = False,
        format: str = "pcd",
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        points: List[services.XyztPoint] = point_cloud_points(
            id, space_bounds, time_bounds, coerce_dt_bounds, user, service_layer
        )

        if format == "pcd":

            try:
                from mppw import pcl
            except Exception as ex:
                logger.warn(
                    f"Could not load PCL bindings, cannot save .pcd file:\n{ex}"
                )
                raise fastapi.exceptions.HTTPException(
                    fastapi.status.HTTP_400_BAD_REQUEST
                )

            outcloud = pcl.PointCloud()
            outcloud.from_list(list(tuple(point.p[0:3]) for point in points))

            tmp_dir = tempfile.TemporaryDirectory("cloudfile")
            cloud_filename = os.path.join(os.path.abspath(tmp_dir.name), "cloud.pcd")

            pcl.save(outcloud, cloud_filename)

            def cleanup():
                shutil.rmtree(os.path.abspath(tmp_dir.name), ignore_errors=True)

            return fastapi.responses.FileResponse(
                cloud_filename,
                media_type="application/x-pcl-pcd",
                background=starlette.background.BackgroundTask(cleanup),
            )

        else:
            raise fastapi.exceptions.HTTPException(fastapi.status.HTTP_400_BAD_REQUEST)

    from .services.artifacts.digital_time_series_services import TimeSeriesServices

    @router.get("/{id}/services/time-series/sample")
    def time_series_sample(
        id: str,
        time_bounds: str = None,
        limit: int = 0,
        est_limit_bytes: int = 0,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):

        artifact: models.DigitalArtifact = read(id, user, service_layer.repo_layer)
        services: TimeSeriesServices = service_layer.artifact_services_for(
            artifact, TimeSeriesServices
        )

        time_bounds = json.loads(time_bounds)
        time_bounds = tuple(arrow.get(bound).datetime for bound in time_bounds)

        cursor = services.sample(artifact, time_bounds, limit, est_limit_bytes)
        return endpoints.StreamingJsonResponse(cursor)

    @router.get("/{id}/services/time-series/bounds")
    def time_series_bounds(
        id: str,
        user: security.ScopedUser = Security(
            request_user(app), scopes=[READ_PROVENANCE_SCOPE]
        ),
        service_layer: services.ServiceLayer = Depends(request_service_layer(app)),
    ):
        artifact: models.DigitalArtifact = read(id, user, service_layer.repo_layer)

        services: TimeSeriesServices = service_layer.artifact_services_for(
            artifact, TimeSeriesServices
        )

        bounds = services.get_bounds(artifact)
        bounds = [str(arrow.get(bounds[0])), str(arrow.get(bounds[1]))]
        return bounds

    return router
