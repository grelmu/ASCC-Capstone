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
import arrow

from mppw_clients import mppw_clients

from .fixtures_api import resolve_bucket_url, build_cloud_url


def create_point_cube(collection, space, x_range, y_range, z_range, t_range):

    collection.insert_one(
        {
            "_id": None,
            "max_scale": space.max_scale,
            "storage_strategy": "xyz_fields",
        }
    )

    cloud_points = []
    for x in x_range:
        for y in y_range:
            for z in z_range:
                for t in t_range:
                    voxel = space.get_vox(x, y, z)
                    collection.insert_one(
                        {
                            "x": x,
                            "y": y,
                            "z": z,
                            "vaddr": voxel.to_addr(),
                            "stamp": arrow.get(t).to("utc").datetime,
                        }
                    )


def test_basic(api_client, api_project, api_bucket):

    """
    Test that we can spatially query a cube of points
    """

    resolved_bucket_url = resolve_bucket_url(api_bucket["url_data"], api_client.api_url)
    cloud_collection_name = __name__.split(".")[-1] + "_basic"
    bucket_collection = pymongo.MongoClient(
        resolved_bucket_url, directConnection=True
    ).get_default_database()[cloud_collection_name]

    space = dbvox.Vox3Space(11)  # +-1024

    create_point_cube(
        bucket_collection, space, range(0, 10), range(0, 10), range(0, 10), range(0, 3)
    )

    cloud_url = build_cloud_url(api_bucket["url_data"], bucket_collection)

    cloud_artifact = api_client.post_json(
        "/artifacts/",
        json={
            "project": api_project["id"],
            "type_urn": "urn:x-mfg:artifact:digital:point-cloud",
            "url_data": cloud_url,
        },
    )

    cloud_query = furl.furl(
        "/artifacts/" + cloud_artifact["id"] + "/services/point-cloud/points"
    )
    cloud_query.query.params["space_bounds"] = json.dumps([(0, 0, 0), (2, 2, 2)])

    points = api_client.get_json(cloud_query.url)
    assert len(points) == (2**3) * 3

    cloud_query.query.params["time_bounds"] = json.dumps([0, 1])

    points = api_client.get_json(cloud_query.url)
    assert len(points) == (2**3) * 1


def test_basic_dt(api_client, api_project, api_bucket):

    """
    Test that we can query spatially with datetimes
    """

    resolved_bucket_url = resolve_bucket_url(api_bucket["url_data"], api_client.api_url)
    cloud_collection_name = __name__.split(".")[-1] + "_basic"
    bucket_collection = pymongo.MongoClient(
        resolved_bucket_url, directConnection=True
    ).get_default_database()[cloud_collection_name]

    space = dbvox.Vox3Space(11)  # +-1024

    create_point_cube(
        bucket_collection,
        space,
        range(0, 5),
        range(0, 5),
        range(0, 5),
        [
            arrow.get(dt_str).datetime
            for dt_str in ["2022-01-01", "2023-01-01", "2024-01-01"]
        ],
    )

    cloud_url = build_cloud_url(api_bucket["url_data"], bucket_collection)

    cloud_artifact = api_client.post_json(
        "/artifacts/",
        json={
            "project": api_project["id"],
            "type_urn": "urn:x-mfg:artifact:digital:point-cloud",
            "url_data": cloud_url,
        },
    )

    cloud_query = furl.furl(
        "/artifacts/" + cloud_artifact["id"] + "/services/point-cloud/points"
    )
    cloud_query.query.params["space_bounds"] = json.dumps([(0, 0, 0), (2, 2, 2)])
    cloud_query.query.params["time_bounds"] = json.dumps(["2022-01-01", "2023-06-01"])
    cloud_query.query.params["coerce_dt_bounds"] = json.dumps(True)

    points = api_client.get_json(cloud_query.url)
    assert len(points) == (2**3) * 2
    for point in points:
        assert arrow.get("2022-01-01") <= arrow.get(point["p"][3])
        assert arrow.get(point["p"][3]) < arrow.get("2023-06-01")


def test_basic_point_cloud_init(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Test that we can initialize a point cloud attached to an operation
    """

    client = api_pytest_client

    operation = client.create_operation(
        {
            "type_urn": "urn:x-mfg:operation:fff",
            "name": "Test Basic Point Cloud Init",
            "description": f"(for testing only)",
        },
        init=True,
    )

    cloud = client.create_artifact(
        {
            "type_urn": "urn:x-mfg:artifact:digital:point-cloud",
        },
        init=False,
    )

    client.add_operation_attachment(
        operation["id"], [":thermal-cloud"], cloud["id"], client.OUTPUT
    )

    cloud = client.init_artifact(cloud["id"])

    assert cloud["url_data"] is not None

    #
    # Load some basic data
    #

    points = []
    for x in range(0, 10):
        for y in range(0, 10):
            for z in range(0, 10):
                for t in [str(arrow.get("2020-01-01")), str(arrow.get("2021-01-01"))]:
                    points.append({"p": [x, y, z, t], "ctx": {"val": x + y + z}})

    client.post_json(
        f"/artifacts/{cloud['id']}/services/point-cloud/insert", json=points
    )

    bounds = client.get_json(f"/artifacts/{cloud['id']}/services/point-cloud/bounds")

    assert bounds is not None

    points_query_furl = furl.furl(
        f"/artifacts/{cloud['id']}/services/point-cloud/points"
    )
    points_query_furl.query.params["space_bounds"] = json.dumps(
        [[-15, -15, -15], [15, 15, 15]]
    )

    points = client.get_json(points_query_furl.url)
    assert len(points) == 2000

    points_query_furl.query.params["space_bounds"] = json.dumps([[0, 0, 0], [5, 5, 5]])
    points_query_furl.query.params["time_bounds"] = json.dumps(
        ["2020-01-01", "2020-01-02"]
    )
    points_query_furl.query.params["coerce_dt_bounds"] = "true"

    points = client.get_json(points_query_furl.url)
    assert len(points) == 125


def test_basic_point_cloud_append(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Test that we can append to a point cloud attached to an operation
    """

    client = api_pytest_client

    operation = client.create_operation(
        {
            "type_urn": "urn:x-mfg:operation:fff",
            "name": "Test Basic Point Cloud Init",
            "description": f"(for testing only)",
        },
        init=True,
    )

    cloud = client.create_artifact(
        {
            "type_urn": "urn:x-mfg:artifact:digital:point-cloud",
        },
        init=False,
    )

    client.add_operation_attachment(
        operation["id"], [":thermal-cloud"], cloud["id"], client.OUTPUT
    )

    cloud = client.init_artifact(cloud["id"])

    assert cloud["url_data"] is not None

    #
    # Load some basic data
    #

    points = []
    for x in range(0, 10):
        for y in range(0, 10):
            for t in [str(arrow.get("2020-01-01")), str(arrow.get("2021-01-01"))]:
                points.append({"p": [x, y, 0, t]})

    client.post_json(
        f"/artifacts/{cloud['id']}/services/point-cloud/insert", json=points
    )

    bounds = client.get_json(f"/artifacts/{cloud['id']}/services/point-cloud/bounds")

    assert bounds[0][0:3] == [0, 0, 0]
    assert arrow.get(bounds[0][3]) == arrow.get("2020-01-01")
    assert bounds[1][0:3] == [9, 9, 0]
    assert arrow.get(bounds[1][3]) == arrow.get("2021-01-01")

    points = [{"p": [-1, -1, -1, str(arrow.get("2019-01-01"))]}]

    client.post_json(
        f"/artifacts/{cloud['id']}/services/point-cloud/insert", json=points
    )

    bounds = client.get_json(f"/artifacts/{cloud['id']}/services/point-cloud/bounds")

    assert bounds[0][0:3] == [-1, -1, -1]
    assert arrow.get(bounds[0][3]) == arrow.get("2019-01-01")
    assert bounds[1][0:3] == [9, 9, 0]
    assert arrow.get(bounds[1][3]) == arrow.get("2021-01-01")

    points = [{"p": [11, 11, 11, str(arrow.get("2023-01-01"))]}]

    client.post_json(
        f"/artifacts/{cloud['id']}/services/point-cloud/insert", json=points
    )

    bounds = client.get_json(f"/artifacts/{cloud['id']}/services/point-cloud/bounds")

    assert bounds[0][0:3] == [-1, -1, -1]
    assert arrow.get(bounds[0][3]) == arrow.get("2019-01-01")
    assert bounds[1][0:3] == [11, 11, 11]
    assert arrow.get(bounds[1][3]) == arrow.get("2023-01-01")

    points_query_furl = furl.furl(
        f"/artifacts/{cloud['id']}/services/point-cloud/points"
    )
    points_query_furl.query.params["space_bounds"] = json.dumps(
        [[-1, -1, -1], [12, 12, 12]]
    )

    points = client.get_json(points_query_furl.url)
    assert len(points) == 202


def test_basic_cloudfile(api_client, api_project, api_bucket):

    """
    Test that we can get a pcl cloud file from the API
    """

    try:
        from mppw import pcl
    except Exception as ex:
        print(f"Not running test - pcl cannot be loaded:\n{ex}")
        return True

    resolved_bucket_url = resolve_bucket_url(api_bucket["url_data"], api_client.api_url)
    cloud_collection_name = __name__.split(".")[-1] + "_basic"
    bucket_collection = pymongo.MongoClient(
        resolved_bucket_url, directConnection=True
    ).get_default_database()[cloud_collection_name]

    space = dbvox.Vox3Space(11)  # +-1024

    create_point_cube(
        bucket_collection, space, range(0, 5), range(0, 5), range(0, 5), [0]
    )

    cloud_url = build_cloud_url(api_bucket["url_data"], bucket_collection)

    cloud_artifact = api_client.post_json(
        "/artifacts/",
        json={
            "project": api_project["id"],
            "type_urn": "urn:x-mfg:artifact:digital:point-cloud",
            "url_data": cloud_url,
        },
    )

    cloud_query = furl.furl(
        "/artifacts/" + cloud_artifact["id"] + "/services/point-cloud/cloudfile"
    )
    cloud_query.query.params["space_bounds"] = json.dumps([(0, 0, 0), (2, 2, 2)])

    with tempfile.TemporaryDirectory("download") as temp_dir:

        response: requests.Response = api_client.get(cloud_query.url)
        if response.status_code != 200:
            raise Exception(f"Failed to get file response:\n{response}")

        cloud_filename = os.path.join(os.path.abspath(temp_dir), "cloud.pcd")
        with open(cloud_filename, "wb") as f:
            f.write(response.content)

        cloud = pcl.load(cloud_filename)

        assert len(cloud.to_list()) == (2**3)
