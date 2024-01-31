import pytest
import requests
import json
import furl
import pymongo
import bson
import arrow
import os
import tempfile
import dbvox
import inspect

import mppw_clients
from mppw import storage

"""
Fixtures that allow testing against an active, local API
"""


@pytest.fixture
def api_storage_layer():
    return storage.MongoDBStorageLayer(
        "mongodb://localhost:27027/mppw?authSource=admin&directConnection=true",
        lambda: ("admin", "password"),
    )


@pytest.fixture
def api_client():
    client = mppw_clients.MppwApiClient("http://localhost:8000/api")
    client.login("admin", "password")
    return client


@pytest.fixture
def api_project(api_client):
    return api_client.post_json("/projects/", json={"name": "Test Project"})


@pytest.fixture
def api_pytest_client(
    api_client: mppw_clients.MppwApiClient, request: pytest.FixtureRequest
):

    """
    A MPPW API client which creates a project for each test module and tags every
    operation and artifact created with a tag containing the particular test name.

    Before running a test, all operations and artifacts with the existing test name
    tag are removed - this allows for inspecting test results in the UI while also
    making it easy to write repeatable tests that assume a clean slate.
    """

    test_name = request.node.name
    module_name = inspect.getmodule(request.node.obj).__name__
    project_name = f"Pytest Project {module_name}"
    test_tag = f"test:{test_name}"

    project = api_client.find_project(name=project_name) or api_client.create_project(
        {"name": project_name}
    )

    operations = api_client.find_operations(tags=[test_tag])
    artifacts = api_client.find_artifacts(tags=[test_tag])
    users = api_client.find_users(local_claim_name=test_tag)

    print(
        f"Deleting {len(operations)} operations,  {len(artifacts)} artifacts, and {len(users)} users with tag {test_tag}..."
    )
    for operation in operations:
        api_client.delete_operation(operation["id"], preserve_data=False)
    for artifact in artifacts:
        api_client.delete_artifact(artifact["id"], preserve_data=False)
    for user in users:
        api_client.delete_user(user["id"], preserve_data=False)
    print(f"Done deleting operations, artifacts, and users with tag {test_tag}.")

    api_client.default_project = project
    api_client.default_tags = [test_tag]
    api_client.default_claims = {"projects": [project["id"]], test_tag: True}

    return api_client


@pytest.fixture
def api_bucket(api_client, api_project):

    bucket_artifact = api_client.post_json(
        "/artifacts/",
        json={
            "project": api_project["id"],
            "type_urn": "urn:x-mfg:artifact:digital:database-bucket",
        },
    )

    return api_client.post_json(
        "/artifacts/" + bucket_artifact["id"] + "/services/artifact/init", json={}
    )


def resolve_bucket_url(bucket_url, api_url):
    bucket_furl = furl.furl(bucket_url)
    api_furl = furl.furl(api_url)
    resolved_bucket_furl = furl.furl(bucket_furl)
    resolved_bucket_furl.host = api_furl.host
    resolved_bucket_furl.port = "27027"
    resolved_bucket_furl.query.params["serverSelectionTimeoutMS"] = 2000
    return resolved_bucket_furl.url


def build_cloud_url(bucket_url, collection):
    cloud_furl = furl.furl(bucket_url)
    cloud_furl.path.segments.append(collection.name)
    cloud_furl.scheme = cloud_furl.scheme + "+dbvox"
    return cloud_furl.url


def build_time_series_url(bucket_url, collection):
    cloud_furl = furl.furl(bucket_url)
    cloud_furl.path.segments.append(collection.name)
    cloud_furl.scheme = cloud_furl.scheme + "+ts"
    return cloud_furl.url
