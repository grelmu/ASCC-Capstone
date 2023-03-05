import pytest
import requests.exceptions

from mppw_clients import mppw_clients


def test_patch_project_basic(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Tests that we can patch a project via the API
    """

    api = api_pytest_client

    api.patch_project(
        api.default_project["id"],
        description="Patched Project",
    )

    patched_project = api.get_project(api.default_project["id"])
    assert patched_project["description"] == "Patched Project"
    assert patched_project["name"] == api.default_project["name"]
