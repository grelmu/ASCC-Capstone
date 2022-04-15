import os
import pyjson5
from .. import models


def load_digital_artifact_json_schema(type_urn: str):

    basename = (
        type_urn.replace(models.DigitalArtifact.URN_PREFIX + ":", "")
        .replace(":", "_")
        .replace("-", "_")
    )
    filename = os.path.join(os.path.dirname(__file__), "artifacts", basename + ".json5")

    if not os.path.exists(filename): return None

    with open(filename, 'r') as f:
        return pyjson5.load(f)


def load_operation_attachment_schema(type_urn: str):

    basename = (
        type_urn.replace(models.Operation.URN_PREFIX + ":", "")
        .replace(":", "_")
        .replace("-", "_")
    )
    filename = os.path.join(
        os.path.dirname(__file__), "operations", basename + ".json5"
    )

    if not os.path.exists(filename): return None

    with open(filename, 'r') as f:
        return pyjson5.load(f)
