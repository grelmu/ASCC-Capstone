from mppw_clients import mppw_clients
import furl


def test_basic_artifact_crud(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Basic test of create, read, update, delete artifact
    """

    api = api_pytest_client

    part = api.create_artifact({"type_urn": ":material:part", "name": "Test Part"})

    part = api.find_artifacts(name="Test Part")[0]

    part["name"] = "Updated Test Part"
    part["label"] = "Updated Label"
    api.update_artifact(part)
    api.patch_artifact(
        part["id"],
        description="Patched Description",
        label=mppw_clients.MppwApiClient.UNDEFINED,
    )

    part = api.get_artifact(part["id"])

    assert "Updated Test Part" == part["name"]
    assert "Patched Description" == part["description"]
    assert part["label"] is None

    api.delete_artifact(part["id"])

    assert 0 == len(api.find_artifacts())


def test_artifact_spatial_frame_update(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Basic test of updating spatial frame, and making sure it's a DbId
    """

    api = api_pytest_client

    parent = api.create_artifact(
        {"type_urn": ":digital:document", "name": "Parent Document"}
    )
    child = api.create_artifact(
        {"type_urn": ":digital:document", "name": "Child Document"}
    )

    spatial_frame = {"parent_frame": parent["id"], "transform": {}}

    api.patch_artifact(child["id"], spatial_frame=spatial_frame)

    child = api.get_artifact(child["id"])

    assert child["spatial_frame"]["parent_frame"] == parent["id"]

    frame_graph_furl = furl.furl(
        f"/artifacts/{parent['id']}/services/artifact/frame_graph"
    )
    frame_graph_furl.query.params["strategy"] = "full"

    frame_graph = api.get_json(frame_graph_furl.url)

    assert len(frame_graph["nodes"]) == 2


def test_artifact_type_query(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Basic test of queries by artifact type
    """

    api = api_pytest_client

    batch = api.create_artifact({"type_urn": ":material:batch", "name": "Test Batch"})
    part = api.create_artifact({"type_urn": ":material:part", "name": "Test Part"})
    doc = api.create_artifact(
        {"type_urn": ":digital:document", "name": "Test Document"}
    )

    found_parts = api.find_artifacts(type_urn=part["type_urn"])

    assert 1 == len(found_parts)
    assert part["name"] == found_parts[0]["name"]

    found_parts = api.find_artifacts(type_urns=[part["type_urn"], batch["type_urn"]])

    assert 2 == len(found_parts)
    assert set([batch["name"], part["name"]]) == set(
        [found_parts[0]["name"], found_parts[1]["name"]]
    )

    found_parts = api.find_artifacts(type_urn_prefix="urn:x-mfg:artifact:material")

    assert 2 == len(found_parts)
    assert set([batch["name"], part["name"]]) == set(
        [found_parts[0]["name"], found_parts[1]["name"]]
    )

    found_paged_parts = api.find_artifacts(type_urns=[part["type_urn"]], paged=True)[
        "results"
    ]

    assert 1 == len(found_paged_parts)
    assert part["name"] == found_paged_parts[0]["name"]

    found_paged_parts = api.find_artifacts(
        type_urns=[part["type_urn"], batch["type_urn"]], paged=True
    )["results"]

    assert 2 == len(found_paged_parts)
    assert set([batch["name"], part["name"]]) == set(
        [found_paged_parts[0]["name"], found_paged_parts[1]["name"]]
    )

    found_paged_parts = api.find_artifacts(
        type_urn_prefix="urn:x-mfg:artifact:material", paged=True
    )["results"]

    assert 2 == len(found_paged_parts)
    assert set([batch["name"], part["name"]]) == set(
        [found_paged_parts[0]["name"], found_paged_parts[1]["name"]]
    )
