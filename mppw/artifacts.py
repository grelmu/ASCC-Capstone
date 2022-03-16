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

from mppw import logger
from . import models
from . import repositories
from .repositories import request_repo_layer
from . import security
from .security import request_user, PROVENANCE_SCOPE
from . import projects
from . import services
from .services import request_service_layer

def create_router(app):

    router = fastapi.APIRouter(prefix="/api/artifacts")

    #
    # CRUD
    #

    @router.post("/", response_model=models.AnyArtifact, status_code = fastapi.status.HTTP_201_CREATED)
    def create(artifact: models.AnyArtifact,
               user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        projects.check_project_claims_for_user(user, [str(artifact.project)])

        art_repo = repo_layer.artifacts
        return art_repo.create(artifact)

    @router.get("/{id}", response_model=models.AnyArtifact)
    def read(id: str,
             user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
             repo_layer = Depends(request_repo_layer(app))):
        
        result = repo_layer.artifacts.query_one(
            id=id,
            project_ids=projects.project_claims_for_user(user)
        )

        if result is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)
        
        return result

    @router.get("/", response_model=List[models.AnyArtifact])
    def query(project_ids: List[str] = fastapi.Query(None),
              active: bool = fastapi.Query(True),
              user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
              repo_layer = Depends(request_repo_layer(app))):

        if project_ids is None:
            project_ids = projects.project_claims_for_user(user)
        
        projects.check_project_claims_for_user(user, project_ids)
        
        return list(repo_layer.artifacts.query(
            project_ids=project_ids,
            active=active,
        ))

    @router.put("/{id}", response_model=bool)
    def update(id: str,
               artifact: models.AnyArtifact,
               current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        if id != str(artifact.id):
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST)

        modified = repo_layer.artifacts.update(artifact, project_ids=projects.project_claims_for_user(current_user))
        
        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.delete("/{id}", response_model=bool)
    def delete(id: str,
               preserve_data: bool = True,
               current_user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
               repo_layer = Depends(request_repo_layer(app))):
        
        modified = (repo_layer.artifacts.deactivate if preserve_data else repo_layer.artifacts.delete)(
            id,
            project_ids=projects.project_claims_for_user(current_user)
        )
        
        if not modified:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    #
    # Services
    #

    @router.post("/{id}/services/artifact/init", response_model=models.Artifact)
    def init(id: str,
             args: dict,
             user: models.User = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
             service_layer: services.ServiceLayer = Depends(request_service_layer(app))):
        
        artifact: models.Artifact = read(id, user, service_layer.repo_layer)
        services = service_layer.artifact_services_for(artifact)
        return services.init(artifact, **args)

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

    @router.get("/{id}/services/file/download", )
    def file_download(id: str,
                      user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                      service_layer: services.ServiceLayer = Depends(request_service_layer(app))):
        
        artifact: models.DigitalArtifact = read(id, user, service_layer.repo_layer)
        service: services.FileServices = service_layer.artifact_service(artifact.type_urn)

        if not service.can_download(artifact):
            return fastapi.responses.RedirectResponse(artifact.url_data)

        meta, data = service.download(artifact)

        if data is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return fastapi.responses.StreamingResponse(data, media_type=meta.content_type)

    @router.get("/{id}/services/file-bucket/download", )
    def file_bucket_download(id: str,
                      path: str,
                      user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                      service_layer: services.ServiceLayer = Depends(request_service_layer(app))):
        
        artifact: models.DigitalArtifact = read(id, user, service_layer.repo_layer)
        service: services.FileBucketServices = service_layer.artifact_service(artifact.type_urn)

        meta, data = service.download(artifact, path)

        if data is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return fastapi.responses.StreamingResponse(data, media_type=meta.content_type)

    @router.post("/{id}/services/file-bucket/upload", response_model=str, status_code = fastapi.status.HTTP_201_CREATED)
    def file_bucket_upload(id: str,
                           path: str = fastapi.Body(None),
                           file: fastapi.UploadFile = fastapi.File(None),
                           user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                           service_layer: services.ServiceLayer = Depends(request_service_layer(app))):
        
        if path is None: raise fastapi.HTTPException(status_code=fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY)
        artifact: models.Artifact = read(id, user, service_layer.repo_layer)

        service: services.FileBucketService = service_layer.artifact_service(artifact.type_urn)
        return service.upload(artifact, path, SyncUploadFile(file))
    
    @router.post("/{id}/services/file-bucket/ls", response_model=List[repositories.BucketFile])
    def file_bucket_ls(id: str,
                       path: str = None,
                       user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                       service_layer: services.ServiceLayer = Depends(request_service_layer(app))):
                    
        artifact: models.Artifact = read(id, user, service_layer.repo_layer)

        service: services.FileBucketService = service_layer.artifact_service(artifact.type_urn)
        return list(service.ls(artifact, path))

    class RenamePaths(pydantic.BaseModel):
        path: str
        new_path: str

    @router.post("/{id}/services/file-bucket/rename", response_model=bool)
    def file_bucket_rename(id: str,
                           rename_paths: RenamePaths,
                           user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                           service_layer: services.ServiceLayer = Depends(request_service_layer(app))):
        
        artifact: models.Artifact = read(id, user, service_layer.repo_layer)

        service: services.FileBucketService = service_layer.artifact_service(artifact.type_urn)
        if not service.rename(artifact, rename_paths.path, rename_paths.new_path):
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)

        return True

    @router.post("/{id}/services/file-bucket/delete", response_model=bool)
    def file_bucket_delete(id: str,
                           path: str = fastapi.Body(None),
                           user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                           service_layer: services.ServiceLayer = Depends(request_service_layer(app))):
        
        if path is None: raise fastapi.HTTPException(status_code=fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY)
        artifact: models.Artifact = read(id, user, service_layer.repo_layer)

        service: services.FileBucketService = service_layer.artifact_service(artifact.type_urn)
        if not service.delete(artifact, path):
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)
        
        return True

    @router.get("/{id}/services/point-cloud/points", response_model=List[services.XyztPoint])
    def point_cloud_points(id: str,
                           space_bounds: str,
                           time_bounds: str = None,
                           coerce_dt_bounds: bool = False,
                           user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                           service_layer: services.ServiceLayer = Depends(request_service_layer(app))):
                    
        artifact: models.Artifact = read(id, user, service_layer.repo_layer)

        space_bounds = json.loads(space_bounds)
        time_bounds = json.loads(time_bounds) if time_bounds else None
        if time_bounds and coerce_dt_bounds:
            time_bounds = tuple(arrow.get(bound).datetime for bound in time_bounds)

        point_cursor = service_layer.get_artifact_service(services.PointCloudServices, artifact).sample(artifact, space_bounds, time_bounds)

        return list(point_cursor)
    
    @router.get("/{id}/services/point-cloud/cloudfile")
    def point_cloud_cloudfile(id: str,
                              space_bounds: str,
                              time_bounds: str = None,
                              coerce_dt_bounds: bool = False,
                              format: str = "pcd",
                              user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                              service_layer: services.ServiceLayer = Depends(request_service_layer(app))):
        
        points: List[services.XyztPoint] = point_cloud_points(id, space_bounds, time_bounds, coerce_dt_bounds, user, service_layer)
        
        if format == "pcd":

            try:
                from mppw import pcl
            except Exception as ex:
                logger.warn(f"Could not load PCL bindings, cannot save .pcd file:\n{ex}")
                raise fastapi.exceptions.HTTPException(fastapi.status.HTTP_400_BAD_REQUEST)

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

    return router
