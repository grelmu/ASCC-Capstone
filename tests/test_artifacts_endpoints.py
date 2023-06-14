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
        part["id"], description="Patched Description", label=mppw_clients.MppwApiClient.UNDEFINED
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

    parent = api.create_artifact({"type_urn": ":digital:document", "name": "Parent Document"})
    child = api.create_artifact({"type_urn": ":digital:document", "name": "Child Document"})

    spatial_frame = { "parent_frame": parent["id"], "transform": {} }

    api.patch_artifact(child["id"], spatial_frame=spatial_frame)

    child = api.get_artifact(child["id"])

    assert child["spatial_frame"]["parent_frame"] == parent["id"]

    frame_graph_furl = furl.furl(f"/artifacts/{parent['id']}/services/artifact/frame_graph")
    frame_graph_furl.query.params["strategy"] = "full"

    frame_graph = api.get_json(frame_graph_furl.url)

    assert len(frame_graph["nodes"]) == 2