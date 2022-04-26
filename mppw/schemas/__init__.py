from email.policy import default
import os
import pyjson5
import glob
import typing

from .. import logger
from .. import models

from .artifact_schema import ArtifactSchema
from .operation_schema import AttachmentsSchema, OperationSchema


def is_compatible_type_urn(generic_type_urn: str, specific_type_urn: str):
    return generic_type_urn == specific_type_urn or specific_type_urn.startswith(
        generic_type_urn + ":"
    )


#
# Artifact schemas
#

ARTIFACT_SCHEMAS = {}


def load_artifact_schemas(dirname: str = None):

    if dirname is None:
        dirname = os.path.dirname(__file__)

    json_filenames = glob.glob(
        os.path.join(dirname, "artifacts", "*.json5")
    ) + glob.glob(os.path.join(dirname, "artifacts", "*.json"))

    for filename in json_filenames:
        with open(filename, "r") as f:
            try:
                value = pyjson5.load(f)
                schema = ArtifactSchema.safe_parse_schema_dict(value)
                ARTIFACT_SCHEMAS[schema.type_urn] = (schema, True)
            except Exception as ex:
                logger.warn(f"Could not parse artifact schema in {filename}:\n{ex}")
                pass


load_artifact_schemas()


def normal_artifact_type_urn_for(type_urn: str):
    if type_urn.startswith(":"):
        return models.Artifact.URN_PREFIX + type_urn
    return type_urn


def get_artifact_schema_type_urns() -> typing.List[str]:
    return sorted(ARTIFACT_SCHEMAS.keys())


def get_artifact_schemas() -> typing.List[ArtifactSchema]:
    return [
        get_artifact_schema(type_urn) for type_urn in get_artifact_schema_type_urns()
    ]


def get_artifact_schema(
    type_urn: str, default_schema_if_missing: bool = False
) -> ArtifactSchema:

    type_urn = normal_artifact_type_urn_for(type_urn)

    schema, _ = ARTIFACT_SCHEMAS.get(type_urn, (None, None))
    if schema is None:
        # If we don't have an exact schema match, look for the most-specific schema match we can find
        for registered_type_urn in reversed(get_artifact_schema_type_urns()):
            if is_compatible_type_urn(registered_type_urn, type_urn):
                return get_artifact_schema(registered_type_urn)

        return ArtifactSchema(type_urn=type_urn) if default_schema_if_missing else None

    # No initialization currently required

    return schema


def load_digital_artifact_json_schema(type_urn: str):

    schema = get_artifact_schema(type_urn)
    if schema is None:
        return None
    return schema.json_schema


#
# Operation schemas
#

OPERATION_SCHEMAS = {}


def load_operation_schemas(dirname: str = None):

    if dirname is None:
        dirname = os.path.dirname(__file__)

    json_filenames = glob.glob(
        os.path.join(dirname, "operations", "*.json5")
    ) + glob.glob(os.path.join(dirname, "operations", "*.json"))

    for filename in json_filenames:
        with open(filename, "r") as f:
            try:
                value = pyjson5.load(f)
                schema = OperationSchema.safe_parse_schema_dict(value)
                OPERATION_SCHEMAS[schema.type_urn] = (schema, False)
            except Exception as ex:
                logger.warn(f"Could not parse operation schema in {filename}:\n{ex}")
                pass


load_operation_schemas()


def normal_operation_type_urn_for(type_urn: str):
    if type_urn.startswith(":"):
        return models.Operation.URN_PREFIX + type_urn
    return type_urn


def get_operation_schema_type_urns() -> typing.List[str]:
    return sorted(OPERATION_SCHEMAS.keys())


def get_operation_schemas() -> typing.List[OperationSchema]:
    return [
        get_operation_schema(type_urn) for type_urn in get_operation_schema_type_urns()
    ]


def get_operation_schema(
    type_urn: str, default_schema_if_missing: bool = False
) -> OperationSchema:

    type_urn = normal_operation_type_urn_for(type_urn)

    schema, initialized = OPERATION_SCHEMAS.get(type_urn, (None, None))
    if schema is None:
        # If we don't have an exact schema match, look for the most-specific schema match we can find
        for registered_type_urn in reversed(get_operation_schema_type_urns()):
            if is_compatible_type_urn(registered_type_urn, type_urn):
                return get_artifact_schema(registered_type_urn)

        return OperationSchema(type_urn=type_urn) if default_schema_if_missing else None

    if not initialized:
        if schema.parent_urns:
            for parent_urn in reversed(schema.parent_urns):
                parent_schema = get_operation_schema(parent_urn)
                if parent_schema is None:
                    continue

                schema.attachments.child_kinds.extend(
                    parent_schema.attachments.child_kinds
                )
                schema.provenance.relations.extend(parent_schema.provenance.relations)

        OPERATION_SCHEMAS[type_urn] = (schema, True)

    return schema
