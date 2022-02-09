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

import json_stream
import json_stream.dump

from mppw import dbvox
from mppw import models

from .fixtures_api import resolve_bucket_url, build_cloud_url, json_response

@pytest.fixture
def api_fff(api_requests, api_project):

    fff_operation = json_response(api_requests.post("/serviced-operations/", json={
        "project": api_project["id"],
        "type_urn": "urn:x-mfg:operation:fff",
        "name": f"FFF for {__name__}",
        "description": f"(for testing only)",
    }))

    return fff_operation

def build_dataset_filename(local_name):
    return os.path.join(os.path.dirname(__file__), "datasets", local_name)

def test_opc_voxelization(api_requests, api_project, api_fff):

    """
    Test that we can store and voxelize an OPC toolpath in an FFF operation
    """

    api_fff = models.Operation(**api_fff)

    fff_bucket_id = api_fff.get_artifacts_of_kind(":process-data")[0].output_artifacts[0].id

    fff_bucket = models.DigitalArtifact(**json_response(api_requests.get(f"/artifacts/{fff_bucket_id}")))

    client = pymongo.MongoClient(resolve_bucket_url(fff_bucket.url_data, api_requests.api_url))
    
    opc_collection = client.get_default_database()["opc"]

    first_x = None
    start_i = None
    end_i = None
    num_points = 10000
    with open(build_dataset_filename("opc_dca632eb3133.json"), 'r') as f:
        arr = json_stream.load(f).persistent()
        for i, item in enumerate(arr):

            if start_i is None:
                if first_x is None: first_x = item["values"]["x"]
                if first_x != item["values"]["x"]:
                    start_i = i
                    end_i = i + num_points

            if start_i is None: continue
            if i >= end_i: break

            item = json.loads(json.dumps(item, default=json_stream.dump.default), object_hook=bson.json_util.object_hook)
            if i == start_i: print(item)
            opc_collection.insert_one(item)

            if (i - start_i)  % 1000 == 0:
                print(f"Wrote {i - start_i} docs...")

    space = dbvox.Vox3Space(21) # +-1024*1024mm

    opc_cloud_collection = client.get_default_database()["opc_cloud"]

    opc_cloud_collection.insert_one({
        "_id": None,
        "max_scale": space.max_scale,
        "storage_strategy": "xyz_fields",
    })

    opc_cloud_collection.create_index([("vaddr", pymongo.ASCENDING), ("stamp", pymongo.ASCENDING)])

    for i, doc in enumerate(opc_collection.find().sort("_id", pymongo.ASCENDING)):
        
        doc = dict(doc)
        doc["x"] = doc["values"]["x"]
        doc["y"] = doc["values"]["y"]
        doc["z"] = doc["values"]["z"]
        doc["stamp"] = doc["values"]["t"]
        del doc["values"]

        voxel = space.get_vox(doc["x"], doc["y"], doc["z"])
        doc["vaddr"] = voxel.to_addr()
        
        if i == 0: print(doc)

        opc_cloud_collection.insert_one(doc)
        if i % 1000 == 0:
            print(f"Voxelized {i} docs...")

    opc_cloud_url = build_cloud_url(fff_bucket.url_data, opc_cloud_collection)

    attachment = json_response(api_requests.post(f"/operations/{api_fff.id}/artifacts/", json={
        "kind_urn": ":toolpath_cloud",
        "new_output_artifacts": [{
            "project": api_project["id"],
            "type_urn": "urn:x-mfg:artifact:digital:point-cloud",
            "url_data": opc_cloud_url,
        }]
    }))

    cloud_artifact = models.DigitalArtifact(**attachment["new_output_artifacts"][0])

    cloud_query = furl.furl(f"/artifacts/{cloud_artifact.id}/services/point-cloud/points")
    cloud_query.query.params["space_bounds"] = json.dumps([(-10000, -10000, -10000), (10000, 10000, 10000)])
    #cloud_query.query.params["time_bounds"] = json.dumps([0, 1])
    
    points = json_response(api_requests.get(cloud_query.url))
    assert len(points) == num_points

    cloud_query.query.params["space_bounds"] = json.dumps([(-1280, -10000, -10000), (-1270, 10000, 10000)])
    #cloud_query.query.params["time_bounds"] = json.dumps([0, 1])
    
    points = json_response(api_requests.get(cloud_query.url))
    assert len(points) == 5

    cloud_query.query.params["space_bounds"] = json.dumps([(-1275, 2189, -2664), (-1274, 2190, -2663)])
    #cloud_query.query.params["time_bounds"] = json.dumps([0, 1])
    
    points = json_response(api_requests.get(cloud_query.url))
    assert len(points) == 1
    assert points[0]["ctx"]["request_id"] == "6137b177b16797bd6b103e14/3397037"

    cloud_query = furl.furl(f"/artifacts/{cloud_artifact.id}/services/point-cloud/cloudfile")
    cloud_query.query.params["space_bounds"] = json.dumps([(-10000, -10000, -10000), (10000, 10000, 10000)])

    response: requests.Response = api_requests.get(cloud_query.url)
    if response.status_code != 200:
        raise Exception(f"Failed to get file response:\n{response}")

    cloud_filename = build_dataset_filename("opc_dca632eb3133.pcd")
    with open(cloud_filename, "wb") as f:
        f.write(response.content)

    