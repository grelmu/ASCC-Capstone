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

from fff_post import mppw_api

@pytest.fixture
def api_client():
    client = mppw_api.MppwClient("http://localhost:8000/api")
    client.login("admin", "password")
    return client

@pytest.fixture
def api_project(api_client):
    return api_client.post_json("/projects/", json={
        "name": "Test Project"
    })

@pytest.fixture
def api_bucket(api_client, api_project):

    bucket_artifact = api_client.post_json("/artifacts/", json={
        "project": api_project["id"],
        "type_urn": "urn:x-mfg:artifact:digital:database-bucket",
    })

    return api_client.post_json("/artifacts/" + bucket_artifact["id"] + "/services/artifact/init", json={})

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
