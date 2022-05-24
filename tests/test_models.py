import pytest
import json

from mppw import models


def test_operation_parse_json():

    """
    Test that we can parse operation models from JSON
    """

    op_data = {
        "project": "pid",
        "type_urn": models.Operation.URN_PREFIX + ":example",
        "artifact_transform_graph": [
            {"kind_urn": ":input", "output_artifacts": ["aid"]}
        ],
    }

    op = models.Operation.parse_raw(json.dumps(op_data))

    assert len(op.attachments.nodes()) == (1 + 1)  # root plus input


def test_operation_read_write_dict():

    """
    Test that we can read/write an operation to a dict nicely
    """

    op_data = {
        "project": "pid",
        "type_urn": models.Operation.URN_PREFIX + ":example",
        "artifact_transform_graph": [
            {"kind_urn": ":input", "output_artifacts": ["aid"]}
        ],
    }

    op = models.Operation.parse_obj(op_data)

    assert len(op.attachments.nodes()) == (1 + 1)  # root plus input

    assert isinstance(op.dict()["artifact_transform_graph"], list)
    assert op.dict()["artifact_transform_graph"][0]["kind_urn"] == ":input"
