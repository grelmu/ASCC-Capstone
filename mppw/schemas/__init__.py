from email.policy import default
import os
import pyjson5
import yaml
import glob
import typing
import pydantic
import importlib.util

from .. import logger
from .. import models

from .artifact_schema import ArtifactSchema
from .operation_schema import AttachmentsSchema, OperationSchema


def is_compatible_type_urn(generic_type_urn: str, specific_type_urn: str):
    return generic_type_urn == specific_type_urn or specific_type_urn.startswith(
        generic_type_urn + ":"
    )


def get_schema_module_names():
    return ["mppw"]


class ModuleSchema(pydantic.BaseModel):
    @staticmethod
    def default_dir_for(model):
        if model == ArtifactSchema:
            return "artifacts"
        if model == OperationSchema:
            return "operations"

    module_schema_model: typing.Any
    module_schema_yaml: typing.Optional[str]
    module_schema_json5: typing.Optional[str]


def load_schemas_in_module(module_name, model):

    module_dir = os.path.dirname(importlib.util.find_spec(module_name).origin)

    schema_dir = os.path.join(
        module_dir, "schemas", ModuleSchema.default_dir_for(model)
    )

    schema_filenames = (
        glob.glob(os.path.join(schema_dir, "*.json5"))
        + glob.glob(os.path.join(schema_dir, "*.json"))
        + glob.glob(os.path.join(schema_dir, "*.yaml"))
        + glob.glob(os.path.join(schema_dir, "*.yml"))
    )

    for filename in schema_filenames:
        with open(filename, "r") as f:
            try:
                schema_yaml, schema_json5 = None, None
                if os.path.splitext(filename)[1].startswith(".json"):
                    schema_json5 = f.read()
                    schema_model = model.safe_parse_schema_dict(
                        pyjson5.loads(schema_json5)
                    )
                else:
                    schema_yaml = f.read()
                    schema_model = model.safe_parse_schema_dict(yaml.load(schema_yaml))

                yield ModuleSchema(
                    module_schema_model=schema_model,
                    module_schema_yaml=schema_yaml,
                    module_schema_json5=schema_json5,
                )
            except Exception as ex:
                logger.warn(f"Could not parse schema in {filename}:\n{ex}")
                raise ex


def load_artifact_schemas_in_module(module_name):
    return load_schemas_in_module(module_name, ArtifactSchema)


def load_operation_schemas_in_module(module_name):
    return load_schemas_in_module(module_name, OperationSchema)


def load_all_schemas_in_module(module_name):
    return list(load_artifact_schemas_in_module(module_name)) + list(
        load_operation_schemas_in_module(module_name)
    )
