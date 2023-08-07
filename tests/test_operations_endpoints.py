from mppw_clients import mppw_clients


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

    api.add_operation_attachment(
        op["id"], [":first"], part["id"], mppw_clients.MppwApiClient.OUTPUT
    )
    api.add_operation_attachment(
        op["id"],
        [":first", part["id"], ":second"],
        file_a["id"],
        mppw_clients.MppwApiClient.OUTPUT,
    )
    api.add_operation_attachment(
        op["id"],
        [":first", part["id"], ":second"],
        file_b["id"],
        mppw_clients.MppwApiClient.OUTPUT,
    )
    api.add_operation_attachment(
        op["id"],
        [":first", part["id"], ":second", file_a["id"], ":third"],
        part_x["id"],
        mppw_clients.MppwApiClient.OUTPUT,
    )
    api.add_operation_attachment(
        op["id"],
        [":first", part["id"], ":second", file_b["id"], ":third"],
        part_y["id"],
        mppw_clients.MppwApiClient.OUTPUT,
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
        op["id"],
        description="Patched Description",
        system_name=mppw_clients.MppwApiClient.UNDEFINED,
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

    graph.attach_artifact(
        build_op, [":output-parts"], built_part, mppw_clients.MppwApiClient.OUTPUT
    )
    graph.attach_artifact(
        machining_op, [":input-parts"], built_part, mppw_clients.MppwApiClient.INPUT
    )
    graph.attach_artifact(
        machining_op,
        [":input-parts", built_part, ":output-parts"],
        machined_part,
        mppw_clients.MppwApiClient.OUTPUT,
    )

    graph.write(api, verbose=True)

    assert 2 == len(api.find_operations())
    assert 2 == len(api.find_artifacts())

    # NOTE: Tags are *or'ed* together, so we need to remove the default ones for this query
    api.default_tags = None
    assert 1 == len(api.find_operations(tags=["test_basic_process_creation_build"]))
    assert 1 == len(api.find_artifacts(tags=["test_basic_process_creation_build"]))


def test_basic_artifact_reclaim(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Basic test of attached artifact reclamation - attaches an artifact to two
    operations and then swaps ownership.
    """

    api = api_pytest_client

    op_a = api.create_operation(
        {"type_urn": ":default", "name": "Test Operation A"}, init=False
    )

    op_b = api.create_operation(
        {"type_urn": ":default", "name": "Test Operation B"}, init=False
    )

    part = api.create_artifact({"type_urn": ":material:part", "name": "Test Part"})

    file_a = api.create_artifact({"type_urn": ":digital:file", "name": "Test File A"})

    file_b = api.create_artifact({"type_urn": ":digital:file", "name": "Test File B"})

    api.add_operation_attachment(
        op_a["id"], [":first"], part["id"], mppw_clients.MppwApiClient.INPUT
    )

    api.add_operation_attachment(
        op_a["id"],
        [":first", part["id"], ":second"],
        file_a["id"],
        mppw_clients.MppwApiClient.OUTPUT,
    )

    api.add_operation_attachment(
        op_b["id"], [":first"], part["id"], mppw_clients.MppwApiClient.INPUT
    )

    api.add_operation_attachment(
        op_a["id"], [":other-first"], part["id"], mppw_clients.MppwApiClient.INPUT
    )

    api.add_operation_attachment(
        op_b["id"],
        [":first", part["id"], ":second"],
        file_b["id"],
        mppw_clients.MppwApiClient.OUTPUT,
    )

    op_a, op_b = api.get_operation(op_a["id"]), api.get_operation(op_b["id"])

    assert (
        mppw_clients.MppwApiClient.INPUT
        == api.find_operation_attachment(op_a, [":first"])[2]
    )
    assert (
        mppw_clients.MppwApiClient.INPUT
        == api.find_operation_attachment(op_a, [":other-first"])[2]
    )
    assert (
        mppw_clients.MppwApiClient.INPUT
        == api.find_operation_attachment(op_b, [":first"])[2]
    )

    assert api.claim_operation_attachment(op_a, [":first"])

    op_a, op_b = api.get_operation(op_a["id"]), api.get_operation(op_b["id"])

    assert (
        mppw_clients.MppwApiClient.OUTPUT
        == api.find_operation_attachment(op_a, [":first"])[2]
    )
    assert (
        mppw_clients.MppwApiClient.INPUT
        == api.find_operation_attachment(op_a, [":other-first"])[2]
    )
    assert (
        mppw_clients.MppwApiClient.INPUT
        == api.find_operation_attachment(op_b, [":first"])[2]
    )

    assert api.claim_operation_attachment(op_b, [":first"])

    op_a, op_b = api.get_operation(op_a["id"]), api.get_operation(op_b["id"])

    assert (
        mppw_clients.MppwApiClient.INPUT
        == api.find_operation_attachment(op_a, [":first"])[2]
    )
    assert (
        mppw_clients.MppwApiClient.INPUT
        == api.find_operation_attachment(op_a, [":other-first"])[2]
    )
    assert (
        mppw_clients.MppwApiClient.OUTPUT
        == api.find_operation_attachment(op_b, [":first"])[2]
    )

    assert (
        mppw_clients.MppwApiClient.OUTPUT
        == api.find_operation_attachment(op_a, [":first", part["id"], ":second"])[2]
    )
    assert (
        mppw_clients.MppwApiClient.OUTPUT
        == api.find_operation_attachment(op_b, [":first", part["id"], ":second"])[2]
    )


def test_operation_type_query(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Basic test of queries by operation type
    """

    api = api_pytest_client

    fff = api.create_operation({"type_urn": ":fff", "name": "Test FFF"})
    compute = api.create_operation(
        {"type_urn": ":compute:default", "name": "Test Compute"}
    )
    machine = api.create_operation(
        {"type_urn": ":prepare:machining", "name": "Test Machining"}
    )
    wjet = api.create_operation(
        {"type_urn": ":prepare:waterjetcut", "name": "Test Waterjet Cut"}
    )

    found_ops = api.find_operations(type_urn=fff["type_urn"])

    assert 1 == len(found_ops)
    assert fff["name"] == found_ops[0]["name"]

    found_ops = api.find_operations(type_urns=[fff["type_urn"], compute["type_urn"]])

    assert 2 == len(found_ops)
    assert set([fff["name"], compute["name"]]) == set(
        [found_ops[0]["name"], found_ops[1]["name"]]
    )

    found_ops = api.find_operations(type_urn_prefix="urn:x-mfg:operation:prepare")

    assert 2 == len(found_ops)
    assert set([machine["name"], wjet["name"]]) == set(
        [found_ops[0]["name"], found_ops[1]["name"]]
    )

    found_paged_ops = api.find_operations(type_urns=[fff["type_urn"]], paged=True)[
        "results"
    ]

    assert 1 == len(found_paged_ops)
    assert fff["name"] == found_paged_ops[0]["name"]

    found_paged_ops = api.find_operations(
        type_urns=[fff["type_urn"], compute["type_urn"]], paged=True
    )["results"]

    assert 2 == len(found_ops)
    assert set([fff["name"], compute["name"]]) == set(
        [found_paged_ops[0]["name"], found_paged_ops[1]["name"]]
    )

    found_paged_ops = api.find_operations(
        type_urn_prefix="urn:x-mfg:operation:prepare", paged=True
    )["results"]

    assert 2 == len(found_ops)
    assert set([machine["name"], wjet["name"]]) == set(
        [found_paged_ops[0]["name"], found_paged_ops[1]["name"]]
    )
