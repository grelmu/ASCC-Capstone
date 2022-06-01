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


def test_process_property_endpoints_create_provenance(
    api_client, api_storage_layer, api_project
):

    """
    Just builds a complex provenance to allow UI testing
    """

    test_process = test_provenance.TestProcessPropertyManufacturingProcess(
        api_storage_layer, mppw.models.Project(**api_project)
    )

    assert True


def test_artifact_frame_graph_endpoint(api_client, api_storage_layer, api_project):

    """
    Tests that we can serialize the frame graph via an endpoint
    """

    test_frame_graph = test_provenance.TestFrameGraph(
        api_storage_layer, mppw.models.Project(**api_project), attach_to_operation=True
    )

    frame_graph = api_client.get_json(
        "/artifacts/" + str(test_frame_graph.mesh.id) + "/services/artifact/frame_graph"
    )

    assert len(frame_graph["nodes"]) == 5
    assert len(frame_graph["edges"]) == 4


def test_artifact_frame_path_endpoint(api_client, api_storage_layer, api_project):

    """
    Tests that we can serialize the frame path via an endpoint
    """

    test_frame_graph = test_provenance.TestFrameGraph(
        api_storage_layer, mppw.models.Project(**api_project), attach_to_operation=True
    )

    frame_path = api_client.get_json(
        "/artifacts/"
        + str(test_frame_graph.mesh.id)
        + "/services/artifact/frame_path?to_id="
        + str(test_frame_graph.mesh2.id)
    )

    assert len(frame_path["path_nodes"]) == 3
    assert len(frame_path["path_edges"]) == 2

    frame_path = api_client.get_json(
        "/artifacts/"
        + str(test_frame_graph.mesh.id)
        + "/services/artifact/frame_path?to_id="
        + str(test_frame_graph.mesh3.id)
    )

    assert frame_path is None
