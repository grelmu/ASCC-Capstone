import pytest
import requests
import json
import furl
import pymongo
import bson
import bson.json_util
import arrow
import os
import tempfile
import dbvox

import json_stream
import json_stream.dump

from mppw import models

from .fixtures_api import resolve_bucket_url, build_cloud_url

def build_dataset_filename(local_name):
    return os.path.join(os.path.dirname(__file__), "datasets", local_name)

@pytest.fixture
def api_fff(api_client, api_project):

    fff_operation = api_client.post_json("/operations/", json={
        "project": api_project["id"],
        "type_urn": "urn:x-mfg:operation:fff",
        "name": f"FFF for {__name__}",
        "description": f"(for testing only)",
    })

    fff_operation = api_client.post_json("/operations/" + fff_operation["id"] + "/services/operation/init", json={})

    fff_bucket_id = api_client.get_attached_artifact_ids_of_kind(fff_operation, ":process-data")[0]
    fff_bucket = models.DigitalArtifact(**api_client.get_json(f"/artifacts/{fff_bucket_id}"))

    client = pymongo.MongoClient(resolve_bucket_url(fff_bucket.url_data, api_client.api_url))

    opc_collection = client.get_default_database()["opc_sample"]

    with open(build_dataset_filename("opc_sample.mdb.json"), 'r') as f:
        opc_docs = json.load(f, object_hook=bson.json_util.object_hook)
        for doc in opc_docs:
            opc_collection.insert_one(doc)

    flir_collection = client.get_default_database()["flir_sample"]

    with open(build_dataset_filename("flir_sample.mdb.json"), 'r') as f:
        flir_docs = json.load(f, object_hook=bson.json_util.object_hook)
        for doc in flir_docs:
            flir_collection.insert_one(doc)

    return fff_operation

def test_opc_voxelization(api_client, api_project, api_fff):

    """
    Test that we can store and voxelize an OPC toolpath in an FFF operation
    """

    # TODO
    pass