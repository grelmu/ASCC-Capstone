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

    fff_operation = api_client.post_json(
        "/operations/",
        json={
            "project": api_project["id"],
            "type_urn": "urn:x-mfg:operation:fff",
            "name": f"FFF for {__name__}",
            "description": f"(for testing only)",
        },
    )

    fff_operation = api_client.post_json(
        "/operations/" + fff_operation["id"] + "/services/operation/init", json={}
    )

    fff_bucket_id = api_client.get_attached_artifact_ids_of_kind(
        fff_operation, ":process-data"
    )[0]
    fff_bucket = models.DigitalArtifact(
        **api_client.get_json(f"/artifacts/{fff_bucket_id}")
    )

    client = pymongo.MongoClient(
        resolve_bucket_url(fff_bucket.url_data, api_client.api_url)
    )

    opc_collection = client.get_default_database()["opc_sample"]

    with open(build_dataset_filename("opc_sample.mdb.json"), "r") as f:
        opc_docs = json.load(f, object_hook=bson.json_util.object_hook)
        for doc in opc_docs[0:12]:
            opc_collection.insert_one(doc)

    flir_collection = client.get_default_database()["flir_sample"]

    with open(build_dataset_filename("flir_sample.mdb.json"), "r") as f:
        flir_docs = json.load(f, object_hook=bson.json_util.object_hook)
        for doc in flir_docs[0:12]:
            flir_collection.insert_one(doc)

    opc_ts_furl = furl.furl(fff_bucket.url_data)
    opc_ts_furl.path.add("opc_sample")
    opc_ts_furl.scheme = "mongodb+ts"

    flir_ts_furl = furl.furl(fff_bucket.url_data)
    flir_ts_furl.path.add("flir_sample")
    flir_ts_furl.scheme = "mongodb+ts"

    for ts_name, ts_url in [("OPC Time Series", opc_ts_furl.url), ("FLIR Time Series", flir_ts_furl.url)]:

        ts = api_client.post_json(
            "/artifacts/",
            json={
                "project": api_project["id"],
                "type_urn": "urn:x-mfg:artifact:digital:time-series",
                "name": ts_name,
                "url_data": ts_url,
            },
        )

        ts = api_client.post_json(
            "/artifacts/" + ts["id"] + "/services/artifact/init", json={}
        )

        ts_attachment = api_client.post_json(
            "/operations/" + fff_operation["id"] + "/artifacts/",
            json={
                "artifact_id": ts["id"],
                "kind_path": [":process-data", str(fff_bucket.id), ":streams"],
                "attachment_mode": "output",
            },
        )

    return fff_operation

def test_opc_voxelization(api_client, api_project, api_fff):

    """
    Test that we can store and voxelize an OPC toolpath in an FFF operation
    """

    # TODO
    pass

def test_time_series_fetch(api_client, api_fff):
    """
    Test that we can fetch the bounds and sample the opc/flir time series
    """
    id = api_fff["id"]
    artifacts = api_client.get_json("/operations/" + id + "/artifacts/all")
    time_series_artifacts = []
    for artifact in artifacts:
        if artifact[1]["type_urn"] == "urn:x-mfg:artifact:digital:time-series":
            time_series_artifacts.append(artifact)
    
    # test the first artifact
    opc_artifact = time_series_artifacts[0][1]
    ts_bounds_query = furl.furl(
        "/artifacts/" + opc_artifact["id"] + "/services/time-series/bounds"
    )
    bounds = api_client.get_json(ts_bounds_query.url)
    assert len(bounds) == 2

    ts_sample_query = furl.furl(
        "/artifacts/" + opc_artifact["id"] + "/services/time-series/sample"
    )
    ts_sample_query.query.params["time_bounds"] = json.dumps([bounds[0],bounds[1]])
    docs = api_client.get_json(ts_sample_query.url)
    assert len(docs) >= 10