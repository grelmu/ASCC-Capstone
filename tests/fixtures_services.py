import pytest

from mppw import models
from mppw import repositories
from mppw import storage
from mppw import services

"""
Fixtures that allow testing against a synthetic storage layer running
on the local machine.

Generally the same database can be used as the active API but the data
won't show up in the API.
"""


@pytest.fixture
def storage_layer():
    return storage.MongoDBStorageLayer(
        "mongodb://localhost:27027/mppw_tests?authSource=admin",
        lambda: ("admin", "password"),
    )


class ServiceLayerContext:

    """
    Testing context to allow creating session-scoped services in unit tests
    """

    def __init__(self, storage_layer: storage.MongoDBStorageLayer):
        self.storage_layer = storage_layer
        self.__exit__(None, None, None)

    def __enter__(self):
        self.session = self.storage_layer.start_session()
        self.cache_session = self.storage_layer.start_cache_session()
        self.repo_layer = repositories.MongoDBRepositoryLayer(
            self.storage_layer, self.session, self.cache_session
        )
        self.service_layer = services.ServiceLayer(self.repo_layer)
        return self.service_layer

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.service_layer = None
        self.repo_layer = None
        if getattr(self, "session", None):
            self.session.end_session()
        self.session = None


@pytest.fixture
def test_project(storage_layer):

    with ServiceLayerContext(storage_layer) as service_layer:

        project_repo: repositories.ProjectRepository = service_layer.repo_layer.projects

        project_name = f"Project {__name__}"
        project = project_repo.query_one(name=project_name)
        if project is None:
            project = project_repo.create(models.Project(name=project_name))
        return project
