from distutils.command.build import build
import json
import furl
import pymongo
import pymongo.collection
import arrow

from .fixtures_api import build_time_series_url, resolve_bucket_url

from mppw_clients import mppw_clients


def create_time_series(collection, t_range, dt_field):

    """
    Add time series documents to a collected based on a range of timestamps (t_range) ordered from oldest to newest
    """

    # Create the timestamped documents
    i = 0
    for t in t_range:
        collection.insert_one(
            {
                "_id": i,
                dt_field: str(t),
            }
        )
        i += 1


def test_time_series_sample(api_client, api_project, api_bucket):

    """
    Test that we can query a collection based on timestamp
    """

    # Setup the collection
    resolved_bucket_url = resolve_bucket_url(api_bucket["url_data"], api_client.api_url)
    ts_collection_name = __name__.split(".")[-1] + "_sample"
    bucket_collection = pymongo.MongoClient(
        resolved_bucket_url, directConnection=True
    ).get_default_database()[ts_collection_name]

    # Add time series data to collection
    time_range = [
        "2022-02-04T16:10:00.200633457Z",
        "2022-02-04T16:10:01.200657914Z",
        "2022-02-04T16:10:02.200619260Z",
        "2022-02-04T16:10:03.200674420Z",
    ]
    create_time_series(bucket_collection, time_range, "timestamp")

    # Create a timeseries artifact
    ts_url = build_time_series_url(api_bucket["url_data"], bucket_collection)

    ts_artifact = api_client.post_json(
        "/artifacts/",
        json={
            "project": api_project["id"],
            "type_urn": "urn:x-mfg:artifact:digital:time-series",
            "url_data": ts_url,
        },
    )

    # obtain the bounds, then sample the docs in the bounds
    ts_bounds_query = furl.furl(
        "/artifacts/" + ts_artifact["id"] + "/services/time-series/bounds"
    )
    bounds = api_client.get_json(ts_bounds_query.url)
    assert len(bounds) == 2


def test_basic_time_series_init(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Test that we can initialize a time series attached to an operation
    """

    client = api_pytest_client

    operation = client.create_operation(
        {
            "type_urn": "urn:x-mfg:operation:prepare:machining",
            "name": "Test Basic Time Series Init",
            "description": f"(for testing only)",
        },
        init=True,
    )

    _, process_data_id, _ = client.find_operation_attachment(
        operation, [":process-data"]
    )

    time_series = client.create_artifact(
        {
            "type_urn": "urn:x-mfg:artifact:digital:time-series",
        },
        init=False,
    )

    client.add_operation_attachment(
        operation["id"],
        [":process-data", process_data_id, ":streams"],
        time_series["id"],
        client.OUTPUT,
    )

    time_series = client.init_artifact(time_series["id"])

    assert time_series["url_data"] is not None

    bounds = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/bounds"
    )
    assert bounds is None

    client.post_json(
        f"/artifacts/{time_series['id']}/services/time-series/insert",
        json=[
            {"stamp": "2020-01-01", "name": "A"},
            {"stamp": "2020-02-02", "name": "B"},
        ],
    )

    bounds = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/bounds"
    )
    assert bounds is not None
    assert bounds == [str(arrow.get("2020-01-01")), str(arrow.get("2020-02-02"))]

    samples = bounds = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/sample?"
        + furl.Query({"time_bounds": json.dumps(bounds)}).encode()
    )

    assert len(samples) == 2
    assert samples[0] == {
        "t": str(arrow.get("2020-01-01")),
        "ctx": {
            "_id": samples[0]["ctx"]["_id"],
            # NOTE that the stored time zone comes back here in UTC but *without* a time zone
            # due to MongoDB
            "stamp": arrow.get("2020-01-01").datetime.replace(tzinfo=None).isoformat(),
            "name": "A",
        },
    }

    stats = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/stats"
    )
    assert stats is not None
    assert stats["size_bytes"] > 0
    assert stats["storage_stats"]["collstats"]["nindexes"] == 5  # _id + auto
    assert stats["storage_stats"]["params"]["dt_field"] == "stamp"


def test_legacy_time_series(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Test that we can use a time series with legacy metadata parameters stored in the
    collection itself.
    """

    client = api_pytest_client

    operation = client.create_operation(
        {
            "type_urn": "urn:x-mfg:operation:prepare:machining",
            "name": "Test Legacy Time Series Init",
            "description": f"(for testing only)",
        },
        init=True,
    )

    _, process_data_id, _ = client.find_operation_attachment(
        operation, [":process-data"]
    )

    time_series = client.create_artifact(
        {
            "type_urn": "urn:x-mfg:artifact:digital:time-series",
        },
        init=False,
    )

    client.add_operation_attachment(
        operation["id"],
        [":process-data", process_data_id, ":streams"],
        time_series["id"],
        client.OUTPUT,
    )

    process_data = client.get_artifact(process_data_id)
    time_series_furl = furl.furl(process_data["url_data"])
    time_series_furl.path.add(f"_art-{time_series['id']}")
    time_series_furl.scheme = "mongodb+ts"
    time_series["url_data"] = time_series_furl.url
    client.update_artifact(time_series)

    bounds = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/bounds"
    )
    assert bounds is None

    time_series_collection: pymongo.collection.Collection = (
        pymongo.MongoClient(
            resolve_bucket_url(process_data["url_data"], client.api_url),
            directConnection=True,
        )
        .get_default_database()
        .get_collection(time_series_furl.path.segments[-1])
    )

    time_series_collection.insert_one(
        {"ts": arrow.get("2020-01-01").datetime, "name": "A"}
    )

    bounds = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/bounds"
    )
    assert bounds is not None
    assert bounds == [str(arrow.get("2020-01-01")), str(arrow.get("2020-01-01"))]

    client.post_json(
        f"/artifacts/{time_series['id']}/services/time-series/insert",
        json=[
            {"ts": "2020-02-02", "name": "B"},
        ],
    )

    bounds = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/bounds"
    )
    assert bounds is not None
    assert bounds == [str(arrow.get("2020-01-01")), str(arrow.get("2020-02-02"))]

    time_series_collection.insert_one(
        {"_id": None, "t_bounds": None, "dt_field": "poststamp", "dt_encoding": None}
    )

    bounds = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/bounds"
    )
    assert bounds is None

    client.post_json(
        f"/artifacts/{time_series['id']}/services/time-series/insert",
        json=[
            {"poststamp": "2020-03-03", "name": "C"},
        ],
    )

    bounds = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/bounds"
    )
    assert bounds is not None
    assert bounds == [str(arrow.get("2020-03-03")), str(arrow.get("2020-03-03"))]

    samples = bounds = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/sample?"
        + furl.Query({"time_bounds": json.dumps(bounds)}).encode()
    )

    assert len(samples) == 1
    assert samples[0] == {
        "t": str(arrow.get("2020-03-03")),
        "ctx": {
            "_id": samples[0]["ctx"]["_id"],
            # NOTE that the stored time zone comes back here in UTC but *without* a time zone
            # due to MongoDB
            "poststamp": arrow.get("2020-03-03")
            .datetime.replace(tzinfo=None)
            .isoformat(),
            "name": "C",
        },
    }

    stats = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/stats"
    )
    assert stats is not None
    assert stats["size_bytes"] > 0
    assert stats["storage_stats"]["collstats"]["nindexes"] == 1  # _id


def test_time_series_init_defaults(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Test that we can initialize a time series and it will correctly insert and
    use field and encoding defaults
    """

    client = api_pytest_client

    operation = client.create_operation(
        {
            "type_urn": "urn:x-mfg:operation:prepare:machining",
            "name": "Test Time Series Id Init",
            "description": f"(for testing only)",
        },
        init=True,
    )

    _, process_data_id, _ = client.find_operation_attachment(
        operation, [":process-data"]
    )

    time_series = client.create_artifact(
        {
            "type_urn": "urn:x-mfg:artifact:digital:time-series",
        },
        init=False,
    )

    client.add_operation_attachment(
        operation["id"],
        [":process-data", process_data_id, ":streams"],
        time_series["id"],
        client.OUTPUT,
    )

    time_series = client.init_artifact(time_series["id"])

    assert time_series["url_data"] is not None

    client.post_json(
        f"/artifacts/{time_series['id']}/services/time-series/insert",
        json=[{"name": "A"}, {"name": "B"}],
    )

    bounds = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/bounds"
    )
    assert bounds is not None
    assert bounds[0] == bounds[1]
    assert arrow.get(bounds[0]) > arrow.get("2000-01-01")

    samples = bounds = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/sample?"
        + furl.Query({"time_bounds": json.dumps(bounds)}).encode()
    )
    assert len(samples) == 2

    stats = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/stats"
    )
    assert stats is not None
    assert stats["storage_stats"]["params"]["dt_field"] == "stamp"
    assert stats["storage_stats"]["params"]["dt_encoding"] == "datetime"


def test_time_series_str_time(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Test that we can initialize a time series using str time
    """

    client = api_pytest_client

    operation = client.create_operation(
        {
            "type_urn": "urn:x-mfg:operation:prepare:machining",
            "name": "Test Time Series Str",
            "description": f"(for testing only)",
        },
        init=True,
    )

    _, process_data_id, _ = client.find_operation_attachment(
        operation, [":process-data"]
    )

    time_series = client.create_artifact(
        {
            "type_urn": "urn:x-mfg:artifact:digital:time-series",
        },
        init=False,
    )

    client.add_operation_attachment(
        operation["id"],
        [":process-data", process_data_id, ":streams"],
        time_series["id"],
        client.OUTPUT,
    )

    time_series = client.init_artifact(
        time_series["id"], dt_field="ros_ts", dt_encoding="str"
    )

    assert time_series["url_data"] is not None

    client.post_json(
        f"/artifacts/{time_series['id']}/services/time-series/insert",
        json=[{"ros_ts": "0001", "name": "A"}, {"ros_ts": "0002", "name": "B"}],
    )

    bounds = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/bounds"
    )
    assert bounds is not None
    assert bounds == ["0001", "0002"]

    samples = bounds = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/sample?"
        + furl.Query({"time_bounds": json.dumps(bounds)}).encode()
    )

    assert len(samples) == 2
    assert samples[0]["t"] == "0001"
    assert samples[1]["t"] == "0002"

    stats = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/stats"
    )
    assert stats is not None
    assert stats["storage_stats"]["collstats"]["nindexes"] == 2


def test_time_series_numeric_time(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Test that we can initialize a time series using very large numeric time, even through the
    JSON APIs
    """

    client = api_pytest_client

    operation = client.create_operation(
        {
            "type_urn": "urn:x-mfg:operation:prepare:machining",
            "name": "Test Time Series Numeric",
            "description": f"(for testing only)",
        },
        init=True,
    )

    _, process_data_id, _ = client.find_operation_attachment(
        operation, [":process-data"]
    )

    time_series = client.create_artifact(
        {
            "type_urn": "urn:x-mfg:artifact:digital:time-series",
        },
        init=False,
    )

    client.add_operation_attachment(
        operation["id"],
        [":process-data", process_data_id, ":streams"],
        time_series["id"],
        client.OUTPUT,
    )

    time_series = client.init_artifact(
        time_series["id"], dt_field="ros_ts", dt_encoding="int"
    )

    assert time_series["url_data"] is not None

    client.post_json(
        f"/artifacts/{time_series['id']}/services/time-series/insert",
        # DRAGONS: Test ints large enough to require true large integer parsing
        json=[
            {"ros_ts": 111111111111111111, "name": "A"},
            {"ros_ts": 222222222222222222, "name": "B"},
        ],
    )

    bounds = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/bounds"
    )
    assert bounds is not None
    assert bounds == [111111111111111111, 222222222222222222]

    samples = bounds = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/sample?"
        + furl.Query({"time_bounds": json.dumps(bounds)}).encode()
    )

    assert len(samples) == 2
    assert samples[0]["t"] == 111111111111111111
    assert samples[1]["t"] == 222222222222222222

    stats = client.get_json(
        f"/artifacts/{time_series['id']}/services/time-series/stats"
    )
    assert stats is not None
    assert stats["storage_stats"]["collstats"]["nindexes"] == 2
