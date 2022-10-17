from mppw_clients import mppw_clients

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
