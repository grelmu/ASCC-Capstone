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

def json_response(response: requests.Response):
    if response.status_code != 200 and response.status_code != 201:
        raise Exception(f"Failed to get json response:\n{response}")
    return response.json()

class ApiRequests:

    def __init__(self, api_url):
        self.api_url = api_url
        self.headers = {}
        for method in ["get", "post", "put", "delete"]:
            setattr(self, method, self._wrap(method))

    def login(self):
        token = json_response(requests.post(self.api_url + "/security/token", data={"username": "admin", "password": "password"}))["access_token"]
        self.headers = { "Authorization": f"Bearer {token}" }

    def _wrap(self, method):

        def wrapped(url, *args, headers=None, **kwargs):
            headers = dict(headers) if headers is not None else {}
            headers.update(self.headers)
            return getattr(requests, method)(self.api_url + url, *args, headers=headers, **kwargs)

        return wrapped

@pytest.fixture
def api_requests():
    _api_requests = ApiRequests("http://localhost:8000/api")
    _api_requests.login()
    return _api_requests

@pytest.fixture
def api_project(api_requests):
    return json_response(api_requests.post("/projects/", json={
        "name": "Test Project"
    }))

@pytest.fixture
def api_bucket(api_requests, api_project):

    bucket_artifact = json_response(api_requests.post("/artifacts/", json={
        "project": api_project["id"],
        "type_urn": "urn:x-mfg:artifact:digital:database-bucket",
    }))

    return json_response(api_requests.post("/artifacts/" + bucket_artifact["id"] + "/services/database-bucket/init"))

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
