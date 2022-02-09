import pytest
import requests
import json
import furl
import pymongo
import bson
import arrow
import os
import tempfile

from mppw import dbvox

from .fixtures_api import resolve_bucket_url, build_cloud_url, json_response

def create_point_cube(collection, space, x_range, y_range, z_range, t_range):

    collection.insert_one({
        "_id": None,
        "max_scale": space.max_scale,
        "storage_strategy": "xyz_fields",
    })

    cloud_points = []
    for x in x_range:
        for y in y_range:
            for z in z_range:
                for t in t_range:
                    voxel = space.get_vox(x, y, z)
                    collection.insert_one({ 
                        "x": x, "y": y, "z": z,
                        "vaddr": voxel.to_addr(),
                        "stamp": t, })

def test_basic(api_requests, api_project, api_bucket):

    """
    Test that we can spatially query a cube of points
    """

    resolved_bucket_url = resolve_bucket_url(api_bucket["url_data"], api_requests.api_url)
    cloud_collection_name = __name__.split(".")[-1] + "_basic"
    bucket_collection = pymongo.MongoClient(resolved_bucket_url).get_default_database()[cloud_collection_name]

    space = dbvox.Vox3Space(11) # +-1024

    create_point_cube(bucket_collection, space, range(0, 10), range(0, 10), range(0, 10), range(0, 3))
    
    cloud_url = build_cloud_url(api_bucket["url_data"], bucket_collection)

    cloud_artifact = json_response(api_requests.post("/artifacts/", json={
        "project": api_project["id"],
        "type_urn": "urn:x-mfg:artifact:digital:point-cloud",
        "url_data": cloud_url,
    }))

    cloud_query = furl.furl("/artifacts/" + cloud_artifact["id"] + "/services/point-cloud/points")
    cloud_query.query.params["space_bounds"] = json.dumps([(0, 0, 0), (2, 2, 2)])
    
    points = json_response(api_requests.get(cloud_query.url))
    assert len(points) == (2 ** 3) * 3

    cloud_query.query.params["time_bounds"] = json.dumps([0, 1])

    points = json_response(api_requests.get(cloud_query.url))
    assert len(points) == (2 ** 3) * 1

def test_basic_dt(api_requests, api_project, api_bucket):

    """
    Test that we can query spatially with datetimes
    """

    resolved_bucket_url = resolve_bucket_url(api_bucket["url_data"], api_requests.api_url)
    cloud_collection_name = __name__.split(".")[-1] + "_basic"
    bucket_collection = pymongo.MongoClient(resolved_bucket_url).get_default_database()[cloud_collection_name]

    space = dbvox.Vox3Space(11) # +-1024

    create_point_cube(bucket_collection, space, range(0, 5), range(0, 5), range(0, 5), [arrow.get(dt_str).datetime for dt_str in ["2022-01-01", "2023-01-01", "2024-01-01"]])
    
    cloud_url = build_cloud_url(api_bucket["url_data"], bucket_collection)

    cloud_artifact = json_response(api_requests.post("/artifacts/", json={
        "project": api_project["id"],
        "type_urn": "urn:x-mfg:artifact:digital:point-cloud",
        "url_data": cloud_url,
    }))

    cloud_query = furl.furl("/artifacts/" + cloud_artifact["id"] + "/services/point-cloud/points")
    cloud_query.query.params["space_bounds"] = json.dumps([(0, 0, 0), (2, 2, 2)])
    cloud_query.query.params["time_bounds"] = json.dumps(["2022-01-01", "2023-06-01"])
    cloud_query.query.params["coerce_dt_bounds"] = json.dumps(True)

    points = json_response(api_requests.get(cloud_query.url))
    assert len(points) == (2 ** 3) * 2
    for point in points:
        assert arrow.get("2022-01-01") <= arrow.get(point["p"][3])
        assert arrow.get(point["p"][3]) < arrow.get("2023-06-01")

def test_basic_cloudfile(api_requests, api_project, api_bucket):

    """
    Test that we can get a pcl cloud file from the API
    """

    try:
        from mppw import pcl
    except Exception as ex:
        print(f"Not running test - pcl cannot be loaded:\n{ex}")
        return True

    resolved_bucket_url = resolve_bucket_url(api_bucket["url_data"], api_requests.api_url)
    cloud_collection_name = __name__.split(".")[-1] + "_basic"
    bucket_collection = pymongo.MongoClient(resolved_bucket_url).get_default_database()[cloud_collection_name]

    space = dbvox.Vox3Space(11) # +-1024

    create_point_cube(bucket_collection, space, range(0, 5), range(0, 5), range(0, 5), [0])
    
    cloud_url = build_cloud_url(api_bucket["url_data"], bucket_collection)

    cloud_artifact = json_response(api_requests.post("/artifacts/", json={
        "project": api_project["id"],
        "type_urn": "urn:x-mfg:artifact:digital:point-cloud",
        "url_data": cloud_url,
    }))

    cloud_query = furl.furl("/artifacts/" + cloud_artifact["id"] + "/services/point-cloud/cloudfile")
    cloud_query.query.params["space_bounds"] = json.dumps([(0, 0, 0), (2, 2, 2)])

    with tempfile.TemporaryDirectory("download") as temp_dir:

        response: requests.Response = api_requests.get(cloud_query.url)
        if response.status_code != 200:
            raise Exception(f"Failed to get file response:\n{response}")

        cloud_filename = os.path.join(os.path.abspath(temp_dir), "cloud.pcd")
        with open(cloud_filename, "wb") as f:
            f.write(response.content)

        cloud = pcl.load(cloud_filename)

        assert len(cloud.to_list()) == (2 ** 3)