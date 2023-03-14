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
from mppw_clients import mppw_clients


def build_dataset_filename(local_name):
    return os.path.join(os.path.dirname(__file__), "datasets", local_name)


@pytest.fixture
def api_fff_builder(api_pytest_client: mppw_clients.MppwApiClient):

    api = api_pytest_client

    def builder(fff_name, num_docs=1024 * 1024):

        fff_operation = api.create_operation(
            {
                "type_urn": "urn:x-mfg:operation:fff",
                "name": fff_name,
                "description": f"(for testing only)",
            },
            init=True,
        )

        fff_bucket = api.get_artifact(
            api.find_operation_attachment(fff_operation, [":process-data"])[1]
        )

        client = pymongo.MongoClient(
            resolve_bucket_url(fff_bucket["url_data"], api.api_url), directConnection=True
        )

        opc_collection = client.get_default_database()["opc_sample"]

        with open(build_dataset_filename("opc_sample.mdb.json"), "r") as f:
            opc_docs = json.load(f, object_hook=bson.json_util.object_hook)
            for doc in opc_docs[0:num_docs]:
                opc_collection.insert_one(doc)

        opc_cloud_collection = client.get_default_database()["opc_cloud"]

        with open(build_dataset_filename("opc_cloud.mdb.json"), "r") as f:
            opc_voxels = json.load(f, object_hook=bson.json_util.object_hook)
            for vox in opc_voxels[0:num_docs]:
                opc_cloud_collection.insert_one(vox)

        flir_collection = client.get_default_database()["flir_sample"]

        with open(build_dataset_filename("flir_sample.mdb.json"), "r") as f:
            flir_docs = json.load(f, object_hook=bson.json_util.object_hook)
            for doc in flir_docs[0:num_docs]:
                flir_collection.insert_one(doc)

        flir_toolhead_collection = client.get_default_database()["flir_toolhead_sample"]

        with open(build_dataset_filename("flir_toolhead_sample.mdb.json"), "r") as f:
            flir_docs = json.load(f, object_hook=bson.json_util.object_hook)
            for doc in flir_docs[0:num_docs]:
                flir_toolhead_collection.insert_one(doc)

        opc_ts_furl = furl.furl(fff_bucket["url_data"])
        opc_ts_furl.path.add("opc_sample")
        opc_ts_furl.scheme = "mongodb+ts"

        flir_ts_furl = furl.furl(fff_bucket["url_data"])
        flir_ts_furl.path.add("flir_sample")
        flir_ts_furl.scheme = "mongodb+ts"

        flir_toolhead_ts_furl = furl.furl(fff_bucket["url_data"])
        flir_toolhead_ts_furl.path.add("flir_toolhead_sample")
        flir_toolhead_ts_furl.scheme = "mongodb+ts"

        for ts_name, ts_url in [
            ("OPC Time Series", opc_ts_furl.url),
            ("FLIR External Time Series", flir_ts_furl.url),
            ("FLIR Toolhead Time Series", flir_toolhead_ts_furl.url),
        ]:

            ts = api.create_artifact(
                {
                    "type_urn": "urn:x-mfg:artifact:digital:time-series",
                    "name": ts_name,
                    "url_data": ts_url,
                },
                init=True,
            )

            api.add_operation_attachment(
                fff_operation["id"],
                [":process-data", fff_bucket["id"], ":streams"],
                ts["id"],
                mppw_clients.MppwApiClient.OUTPUT,
            )

        opc_pc_furl = furl.furl(fff_bucket["url_data"])
        opc_pc_furl.path.add("opc_cloud")
        opc_pc_furl.scheme = "mongodb+dbvox"

        pc = api.create_artifact(
            {
                "type_urn": "urn:x-mfg:artifact:digital:point-cloud",
                "name": "OPC Point Cloud",
                "url_data": opc_pc_furl.url,
            },
            init=True,
        )

        api.add_operation_attachment(
            fff_operation["id"],
            [":toolpath-cloud"],
            pc["id"],
            mppw_clients.MppwApiClient.OUTPUT,
        )

        return fff_operation

    return builder


def test_opc_voxelization(api_client, api_project, api_fff_builder):

    """
    Test that we can store and voxelize an OPC toolpath in an FFF operation
    """

    # TODO
    pass


def test_time_series_fetch(api_client, api_fff_builder):

    """
    Test that we can fetch the bounds and sample the opc/flir time series
    """

    api_fff = api_fff_builder("FFF for Test Time Series Fetch")

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
    ts_sample_query.query.params["time_bounds"] = json.dumps([bounds[0], bounds[1]])
    docs = api_client.get_json(ts_sample_query.url)
    assert len(docs) >= 10
