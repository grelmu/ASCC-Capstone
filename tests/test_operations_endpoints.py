from mppw_clients import mppw_clients
from mppw_clients.mppw_clients.mppw_api_client import MppwApiClient


def test_basic_operation_craud(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Basic test of create, read, attach, update, delete operation
    """

    api = api_pytest_client

    op = api.create_operation(
        {"type_urn": ":default", "name": "Test Operation"}, init=False
    )

    part = api.create_artifact({"type_urn": ":material:part", "name": "Test Part"})

    file_a = api.create_artifact({"type_urn": ":digital:file", "name": "Test File A"})
    file_b = api.create_artifact({"type_urn": ":digital:file", "name": "Test File B"})

    part_x = api.create_artifact({"type_urn": ":material:part", "name": "Test Part X"})
    part_y = api.create_artifact({"type_urn": ":material:part", "name": "Test Part Y"})

    api.add_operation_attachment(op["id"], [":first"], part["id"], MppwApiClient.OUTPUT)
    api.add_operation_attachment(
        op["id"], [":first", part["id"], ":second"], file_a["id"], MppwApiClient.OUTPUT
    )
    api.add_operation_attachment(
        op["id"], [":first", part["id"], ":second"], file_b["id"], MppwApiClient.OUTPUT
    )
    api.add_operation_attachment(
        op["id"],
        [":first", part["id"], ":second", file_a["id"], ":third"],
        part_x["id"],
        MppwApiClient.OUTPUT,
    )
    api.add_operation_attachment(
        op["id"],
        [":first", part["id"], ":second", file_b["id"], ":third"],
        part_y["id"],
        MppwApiClient.OUTPUT,
    )

    op = api.find_operations(name="Test Operation")[0]

    assert 5 == len(api.find_operation_attachments(op, ["**"]))
    assert 1 == len(api.find_operation_attachments(op, [":first"]))
    assert 2 == len(api.find_operation_attachments(op, [":first", "*", ":second"]))
    assert 2 == len(
        api.find_operation_attachments(op, [":first", "*", ":second", "*", ":third"])
    )

    op["name"] = "Updated Test Operation"
    op["system_name"] = "Updated System Name"
    api.update_operation(op)
    api.patch_operation(
        op["id"], description="Patched Description", system_name=MppwApiClient.UNDEFINED
    )

    op = api.get_operation(op["id"])

    assert "Updated Test Operation" == op["name"]
    assert "Patched Description" == op["description"]
    assert op["system_name"] is None

    api.delete_operation(op["id"])

    assert 0 == len(api.find_operations())

    # Reenable so we can browse operation
    api.patch_operation(op["id"], active=True)


def test_basic_process_creation(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Basic test of process creation via graph
    """

    api = api_pytest_client

    graph = mppw_clients.MppwProcessGraph()

    build_op = graph.add_operation_node(
        {
            "type_urn": ":fff",
            "name": "Process Build",
            "tags": ["test_basic_process_creation_build"],
        }
    )
    machining_op = graph.add_operation_node(
        {"type_urn": ":prepare:machining", "name": "Process Machining"}
    )
    built_part = graph.add_artifact_node(
        {
            "type_urn": ":material:part",
            "name": "Built Part",
            "tags": ["test_basic_process_creation_build"],
        }
    )
    machined_part = graph.add_artifact_node(
        {"type_urn": ":material:part", "name": "Machined Part"}
    )

    graph.attach_artifact(build_op, [":output-parts"], built_part, MppwApiClient.OUTPUT)
    graph.attach_artifact(
        machining_op, [":input-parts"], built_part, MppwApiClient.INPUT
    )
    graph.attach_artifact(
        machining_op,
        [":input-parts", built_part, ":output-parts"],
        machined_part,
        MppwApiClient.OUTPUT,
    )

    graph.write(api, verbose=True)

    assert 2 == len(api.find_operations())
    assert 2 == len(api.find_artifacts())

    # NOTE: Tags are *or'ed* together, so we need to remove the default ones for this query
    api.default_tags = None
    assert 1 == len(api.find_operations(tags=["test_basic_process_creation_build"]))
    assert 1 == len(api.find_artifacts(tags=["test_basic_process_creation_build"]))
