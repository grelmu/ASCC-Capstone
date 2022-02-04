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

from mppw import logger
from . import models
from . import repositories
from .repositories import request_repo_layer
from . import security
from .security import request_user, PROVENANCE_SCOPE
from . import projects
from . import services
from .services import DatabaseBucketServices, XyztPoint, request_service_layer

def create_router(app):

    router = fastapi.APIRouter(prefix="/api/artifacts")

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

    @router.post("/{id}/services/database-bucket/init", response_model=models.DigitalArtifact)
    def database_bucket_init(id: str,
                             scheme: str = None,
                             user: security.ScopedUser = Security(request_user(app), scopes=[PROVENANCE_SCOPE]),
                             service_layer: services.ServiceLayer = Depends(request_service_layer(app))):
                    
        artifact: models.Artifact = read(id, user, service_layer.repo_layer)

        service_layer.get_artifact_service(DatabaseBucketServices, artifact).init(artifact, scheme=scheme)
        return artifact

    @router.get("/{id}/services/point-cloud/points", response_model=List[XyztPoint])
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
        
        points: List[XyztPoint] = point_cloud_points(id, space_bounds, time_bounds, coerce_dt_bounds, user, service_layer)
        
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

    return router
