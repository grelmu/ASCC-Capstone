from webbrowser import Opera
import pydantic
import pyjson5
from typing import List, Union, Optional, ForwardRef, Any

class ServicesSchema(pydantic.BaseModel):

    class_qualname: Optional[str]

class ArtifactSchema(pydantic.BaseModel):

    """
    Schema which defines artifact classes
    """

    type_urn: str
    parent_urns: Optional[List[str]]
    name: Optional[str]
    description: Optional[str]
    json_schema: Any
    services: ServicesSchema = pydantic.Field(ServicesSchema())

    @staticmethod
    def safe_parse_schema_dict(value: dict, type_urn: str = ""):

        if "type_urn" not in value:
            value = {"type_urn": type_urn, "json_schema": value}

        return ArtifactSchema.parse_obj(value)
