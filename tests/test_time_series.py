from distutils.command.build import build
import json
import furl
import pymongo

from .fixtures_api import build_time_series_url, resolve_bucket_url


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
