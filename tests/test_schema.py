import pytest
import json

from mppw import schemas

"""
Unit tests of schemas for operations and artifacts
"""


def test_attachment_schema_parse():

    """
    Test that we can parse regular and compact attachment schema
    """

    schema_value = {
        "child_kinds": [
            {
                "kind_urn": ":foo",
                "types": [
                    {
                        "type_urn": ":bar",
                        "child_kinds": [
                            {"kind_urn": ":biz", "types": [{"type_urn": ":baz"}]}
                        ],
                    }
                ],
            },
        ]
    }

    schema = schemas.AttachmentsSchema.parse_raw(json.dumps(schema_value))

    assert schema.child_kinds[0].kind_urn == ":foo"
    assert schema.child_kinds[0].types[0].type_urn == ":bar"
    assert schema.child_kinds[0].types[0].child_kinds[0].kind_urn == ":biz"
    assert schema.child_kinds[0].types[0].child_kinds[0].types[0].type_urn == ":baz"

    schema_value = {
        ":foo": [(":bar", {":biz": [":baz"]})],
    }

    assert schemas.AttachmentsSchema.is_compact_schema_dict(schema_value)
    schema = schemas.AttachmentsSchema.parse_compact_schema_dict(schema_value)

    assert schema.child_kinds[0].kind_urn == ":foo"
    assert schema.child_kinds[0].types[0].type_urn == ":bar"
    assert schema.child_kinds[0].types[0].child_kinds[0].kind_urn == ":biz"
    assert schema.child_kinds[0].types[0].child_kinds[0].types[0].type_urn == ":baz"


def test_parse_operation_schema():

    """
    Test that we can read and write operation schemas
    """

    schema_value = {
        "type_urn": ":type",
        "attachments": {
            "child_kinds": [
                {
                    "kind_urn": ":foo",
                    "types": [
                        {
                            "type_urn": ":bar",
                            "child_kinds": [
                                {"kind_urn": ":biz", "types": [{"type_urn": ":baz"}]}
                            ],
                        }
                    ],
                },
            ]
        },
        "provenance": {},
        "services": {"class_qualname": "module:ClassName"},
    }

    attachments_compact = {
        ":foo": [(":bar", {":biz": [":baz"]})],
    }

    for i in range(0, 3):

        # Regular
        if i == 0:
            pass

        # Compact attachments
        if i == 1:
            schema_value["attachments"] = attachments_compact

        # Just attachments
        if i == 2:
            schema_value = schema_value["attachments"]

        schema = schemas.OperationSchema.safe_parse_schema_dict(schema_value)

        assert schema.attachments.child_kinds[0].kind_urn == ":foo"
        assert schema.attachments.child_kinds[0].types[0].type_urn == ":bar"
        assert (
            schema.attachments.child_kinds[0].types[0].child_kinds[0].kind_urn == ":biz"
        )
        assert (
            schema.attachments.child_kinds[0].types[0].child_kinds[0].types[0].type_urn
            == ":baz"
        )

        if i != 2:
            print(schema_value)
            assert schema.services.class_qualname == "module:ClassName"


def test_load_operation_schema():

    """
    Test that we can load a sample schema with a parent reference
    """

    schema = schemas.get_operation_schema("urn:x-mfg:operation:fff")

    child_kind_urns = list(map(lambda k: k.kind_urn, schema.attachments.child_kinds))

    assert ":toolpath" in child_kind_urns
    assert ":attachments" in child_kind_urns
    assert len(schema.provenance.steps) == 2


def test_parse_artifact_schema():

    """
    Test that we can read artifact schemas
    """

    schema_value = {
        "type_urn": ":type",
        "json_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "title": "TestObject",
            "properties": {},
        },
        "services": {"class_qualname": "module:ClassName"},
    }

    schema = schemas.ArtifactSchema.safe_parse_schema_dict(schema_value)

    assert schema.type_urn == ":type"
    assert schema.json_schema["title"] == "TestObject"
    assert schema.services.class_qualname == "module:ClassName"


def test_load_artifact_schema():

    """
    Test that we can load a sample schema with a parent reference
    """

    schema = schemas.get_artifact_schema("urn:x-mfg:artifact:digital:file")

    assert (
        schema.services.class_qualname
        == "mppw.services.artifacts.digital_file_services:FileServices"
    )
    assert schema.name == "File"
