import pytest

import mppw.models
from . import test_provenance


def test_operation_provenance_steps_endpoint(
    api_client, api_storage_layer, api_project
):

    """
    Tests that we can serialize the provenance steps via an endpoint
    """

    test_process = test_provenance.TestBasicManufacturingProcess(
        api_storage_layer, mppw.models.Project(**api_project)
    )

    steps = api_client.get_json(
        "/operations/"
        + str(test_process.fff.id)
        + "/services/operation/provenance/steps"
    )

    assert len(steps["nodes"]) == 3 + 2
    assert len(steps["edges"]) == 4


def test_artifact_provenance_endpoint(api_client, api_storage_layer, api_project):

    """
    Tests that we can serialize artifact provenance via an endpoint
    """

    test_process = test_provenance.TestBasicManufacturingProcess(
        api_storage_layer, mppw.models.Project(**api_project)
    )

    provenance = api_client.get_json(
        "/artifacts/" + str(test_process.specimen.id) + "/services/artifact/provenance"
    )

    assert len(provenance["nodes"]) == 3 + 2
    assert len(provenance["edges"]) == 4

    provenance = api_client.get_json(
        "/artifacts/"
        + str(test_process.specimen.id)
        + "/services/artifact/provenance?strategy=ancestors%2b2"
    )

    assert len(provenance["nodes"]) == (3 + 2) + (1 + 1)
    assert len(provenance["edges"]) == 4 + 2

    provenance = api_client.get_json(
        "/artifacts/"
        + str(test_process.batch.id)
        + "/services/artifact/provenance?strategy=descendants"
    )

    assert len(provenance["nodes"]) == (3 + 2) + (1 + 1)
    assert len(provenance["edges"]) == 4 + 2


def test_process_property_endpoints_provenance(
    api_client, api_storage_layer, api_project
):

    test_process = test_provenance.TestProcessPropertyManufacturingProcess(
        api_storage_layer, mppw.models.Project(**api_project)
    )

    assert True
