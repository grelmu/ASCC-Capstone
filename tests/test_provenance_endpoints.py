import pytest
import furl
import pandas

import mppw
import mppw_clients

from mppw.tests import test_provenance


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


def test_project_provenance_query_endpoint(
    api_client: mppw_clients.MppwApiClient, api_storage_layer, api_project
):
    """
    Tests that we can serialize a provenance query via an endpoint
    """

    process_with_geometry = test_provenance.TestBasicManufacturingProcessWithGeometry(
        api_storage_layer, mppw.models.Project(**api_project)
    )

    query_furl = furl.furl(
        f"/projects/{api_project['id']}/services/project/provenance/"
    )
    query_furl.query.params.add("from_artifact_ids", process_with_geometry.specimen.id)
    query_furl.query.params.add("from_artifact_ids", process_with_geometry.wall.id)
    query_furl.query.params[
        "cypher_query"
    ] = """
        MATCH (TC:ArtifactNode)<--(FFF:OperationStepNode)-[*1..99]->(CUT:OperationStepNode)-->(S:ArtifactNode) 
        WHERE
            TC.type_urn = "urn:x-mfg:artifact:digital:point-cloud" AND
            FFF.type_urn = "urn:x-mfg:operation:fff" AND
            CUT.type_urn = "urn:x-mfg:operation:prepare:waterjetcut" AND
            S.type_urn = "urn:x-mfg:artifact:material:part"
        RETURN TC, S
        """
    query_furl.query.params["strategy"] = "ancestors+2"

    results = api_client.get_json(query_furl.url)

    results_df = pandas.DataFrame(results).applymap(lambda r: r["artifact_id"])
    assert results_df["TC"].iloc[0] == str(process_with_geometry.thermal_cloud.id)
    assert results_df["S"].iloc[0] == str(process_with_geometry.specimen.id)

    # Translate query to a POST query

    body_query = {
        "from_artifact_ids": [
            str(id) for id in query_furl.query.params.allvalues("from_artifact_ids")
        ],
        "cypher_query": query_furl.query.params["cypher_query"],
        "strategy": query_furl.query.params["strategy"],
    }
    query_furl.query = None

    results = api_client.post_json(query_furl.url, json=body_query)

    results_df = pandas.DataFrame(results).applymap(lambda r: r["artifact_id"])
    assert results_df["TC"].iloc[0] == str(process_with_geometry.thermal_cloud.id)
    assert results_df["S"].iloc[0] == str(process_with_geometry.specimen.id)

    # Nearest related query

    nearest_related_furl = furl.furl(
        f"/artifacts/{process_with_geometry.specimen.id}/services/artifact/provenance/nearest_related_frame_path"
    )
    nearest_related_furl.query.params[
        "related_artifact_cypher_query"
    ] = """
        MATCH (P:ArtifactNode)-->(S)-->(B:ArtifactNode) 
        WHERE
            P.type_urn = "urn:x-mfg:artifact:material:part" AND
            B.type_urn = "urn:x-mfg:artifact:digital:document:bounding-box"
        RETURN B
        """
    nearest_related_furl.query.params["to_id"] = str(
        process_with_geometry.thermal_cloud.id
    )
    nearest_related_furl.query.params["strategy"] = "ancestors+2"

    paths = api_client.get_json(nearest_related_furl.url)

    assert paths["provenance_path"]["path_nodes"][0]["artifact_id"] == str(
        process_with_geometry.specimen.id
    )
    assert paths["provenance_path"]["path_nodes"][-1]["artifact_id"] == str(
        process_with_geometry.specimen_bbox.id
    )
    assert paths["frame_path"]["path_nodes"][0]["artifact_id"] == str(
        process_with_geometry.specimen_bbox.id
    )
    assert paths["frame_path"]["path_nodes"][-1]["artifact_id"] == str(
        process_with_geometry.thermal_cloud.id
    )

    # Test when no frame path exists
    nearest_related_furl.path = f"/artifacts/{process_with_geometry.batch.id}/services/artifact/provenance/nearest_related_frame_path"

    paths = api_client.get_json(nearest_related_furl.url)

    assert paths is None
