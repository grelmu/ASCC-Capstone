from webbrowser import Opera
import pydantic
import pyjson5
from typing import List, Union, Optional, ForwardRef

_AttachmentTypeNodeRef = ForwardRef("AttachmentsSchema.TypeNode")
_AttachmentKindNodeRef = ForwardRef("AttachmentsSchema.KindNode")


class AttachmentsSchema(pydantic.BaseModel):
    class KindNode(pydantic.BaseModel):
        kind_urn: str
        types: List[_AttachmentTypeNodeRef]

    class TypeNode(pydantic.BaseModel):
        type_urn: str
        child_kinds: List[_AttachmentKindNodeRef] = pydantic.Field(
            default_factory=lambda: []
        )

    child_kinds: List[KindNode] = pydantic.Field(default_factory=lambda: [])

    @staticmethod
    def is_compact_schema_dict(value: dict):
        return len(value.keys()) > 1 or (
            len(value.keys()) == 1 and list(value.keys())[0] != "child_kinds"
        )

    @staticmethod
    def parse_compact_schema_dict(value: dict):
        root_type = AttachmentsSchema._parse_compact_schema_type(("", value))
        return AttachmentsSchema(child_kinds=root_type.child_kinds)

    @staticmethod
    def _parse_compact_schema_type(type_value: Union[str, tuple]):
        if isinstance(type_value, str):
            return AttachmentsSchema.TypeNode(type_urn=type_value, child_kinds=[])
        return AttachmentsSchema.TypeNode(
            type_urn=type_value[0],
            child_kinds=AttachmentsSchema._parse_compact_schema_kind(type_value[1]),
        )

    @staticmethod
    def _parse_compact_schema_kind(kind_value: dict):
        kinds = []
        for kind_urn, types in kind_value.items():
            kind = AttachmentsSchema.KindNode(kind_urn=kind_urn, types=[])
            for type in types:
                kind.types.append(AttachmentsSchema._parse_compact_schema_type(type))
            kinds.append(kind)

        return kinds


AttachmentsSchema.TypeNode.update_forward_refs()
AttachmentsSchema.KindNode.update_forward_refs()


class ProvenanceSchema(pydantic.BaseModel):
    class Step(pydantic.BaseModel):
        name: Optional[str]
        context: Optional[str]
        from_artifacts: List[str] = pydantic.Field(default_factory=lambda: [])
        to_artifacts: List[str] = pydantic.Field(default_factory=lambda: [])
        is_source: bool = False
        is_sink: bool = False

    steps: List[Step] = pydantic.Field(default_factory=lambda: [])


class ServicesSchema(pydantic.BaseModel):

    class_qualname: Optional[str]


class OperationSchema(pydantic.BaseModel):

    type_urn: str
    parent_urns: Optional[List[str]]
    name: Optional[str]
    description: Optional[str]
    attachments: AttachmentsSchema = pydantic.Field(AttachmentsSchema())
    provenance: ProvenanceSchema = pydantic.Field(ProvenanceSchema())
    services: ServicesSchema = pydantic.Field(ServicesSchema())

    @staticmethod
    def safe_parse_schema_dict(value: dict, type_urn: str = ""):

        if "type_urn" not in value:
            value = {"type_urn": type_urn, "attachments": value}

        if "attachments" in value and AttachmentsSchema.is_compact_schema_dict(
            value["attachments"]
        ):
            value["attachments"] = AttachmentsSchema.parse_compact_schema_dict(
                value["attachments"]
            ).dict()

        return OperationSchema.parse_obj(value)
