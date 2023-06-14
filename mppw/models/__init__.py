from typing import Optional, List, Sequence, ClassVar, Any, Tuple, Union, Dict
import fastapi
import fastapi.encoders
import pydantic
import bson
import datetime
import enum
import networkx
import re
import json
import hashlib

from mppw import logger

from .. import schemas

"""
Data models for the storage layer

TODO: Break this up into dedicated files
"""


class DbId:

    """
    A DbId is a data type to transparently manage the transition between ObjectIds and str ids

    During (de-)serialization, a DbId can be parsed and encoded to an ObjectId (when writing to Bson) or a str (when writing to JSON)
    """

    @staticmethod
    def init(val):
        return DbId.validate(val)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, val):
        if isinstance(val, DbId):
            return val
        if isinstance(val, bson.ObjectId):
            return ObjectDbId(val)
        if isinstance(val, str):
            try:
                return ObjectDbId(bson.ObjectId(val))
            except:
                return StrDbId(val)
        else:
            raise Exception(f"Unknown db id value of {val}")

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

    @classmethod
    def bson_encoder(cls):
        class BsonEncoder(bson.codec_options.TypeEncoder):
            python_type = cls

            def transform_python(self, value):
                return value.id

        return BsonEncoder()


class ObjectDbId(DbId):
    def __init__(self, id: bson.ObjectId):
        self.id = id

    def __str__(self):
        return str(self.id)

    def __repr__(self):
        return f"DbId(ObjectId({self.id}))"

    def __json__(self):
        return str(self.id)


class StrDbId(DbId):
    def __init__(self, id: str):
        self.id = id

    def __str__(self):
        return self.id

    def __repr__(self):
        return f"DbId({self.id})"

    def __json__(self):
        return self.id


class BaseJsonModel(pydantic.BaseModel):

    """
    Model which manages serialization of types that are nontrivial in JSON (dates, ObjectIds)
    """

    class Config(pydantic.BaseConfig):
        json_encoders = {
            datetime.datetime: lambda dt: dt.isoformat(),
            ObjectDbId: lambda dbid: dbid.__json__(),
            StrDbId: lambda dbid: dbid.__json__(),
            bson.ObjectId: lambda oid: str(oid),
        }

    @staticmethod
    def to_json(value):
        class SerializeModel(BaseJsonModel):
            v: Any

        ser_model = SerializeModel(v=value)
        return ser_model.json()[len('{"v":') : -1]


class DocModel(BaseJsonModel):
    id: Optional[DbId]


#
# Config settings
#


class ConfigKv(pydantic.BaseModel):
    key: str
    value: Optional[str]


#
# Users and Security
#


class SafeUser(DocModel):
    username: str
    allowed_scopes: Optional[List[str]]
    local_claims: Optional[Dict[str, Any]]
    active: bool = True


class User(SafeUser):
    hashed_password: str


# class Scope(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     name: str
#     description: str

#
# Projects
#


class Project(DocModel):
    name: str
    description: Optional[str]

    included_schema_modules: Optional[List[str]]

    active: bool = True


#
# Artifacts
#


class GeometryLabel(pydantic.BaseModel):
    name: str
    coordinate: List[float]


class Artifact(DocModel):

    URN_PREFIX: ClassVar = "urn:x-mfg:artifact"

    # Keep these required for later use in sharding and vfs interfaces
    type_urn: str
    project: DbId

    name: Optional[str]
    description: Optional[str]
    tags: Optional[List[str]]
    active: bool = True


class MaterialArtifact(Artifact):

    URN_PREFIX: ClassVar = f"{Artifact.URN_PREFIX}:material"

    material_system_urn: Optional[str]

    label: Optional[str]
    geometry_labels: Optional[List[GeometryLabel]]
    location_label: Optional[str]

    @pydantic.validator("type_urn")
    def valid_type_urn_prefix(cls, v):
        if not v.startswith(MaterialArtifact.URN_PREFIX):
            raise ValueError(
                f"material artifact URNs must start with {MaterialArtifact.URN_PREFIX}: {v}"
            )
        return v


class SpatialFrame(pydantic.BaseModel):

    parent_frame: Optional[DbId]
    transform: Any


class DigitalArtifact(Artifact):

    URN_PREFIX: ClassVar = f"{Artifact.URN_PREFIX}:digital"

    local_data: Any
    url_data: Optional[str]

    spatial_frame: Optional[SpatialFrame]

    @pydantic.validator("type_urn")
    def valid_type_urn_prefix(cls, v):
        if not v.startswith(DigitalArtifact.URN_PREFIX):
            raise ValueError(
                f"digital artifact URNs must start with {DigitalArtifact.URN_PREFIX}: {v}"
            )
        return v
    
    def dict(self, *args, **kwargs):
        values = super().dict(*args, **kwargs)
        # Force spatial frame parent frames to DbIds
        if values.get("spatial_frame") is not None:
            if values["spatial_frame"]["parent_frame"] is not None:
                values["spatial_frame"]["parent_frame"] = DbId.init(values["spatial_frame"]["parent_frame"])
        return values


AnyArtifact = Union[MaterialArtifact, DigitalArtifact]

#
# Operations and Provenance
#


class ArtifactTransform(BaseJsonModel):

    """
    Currently this data model is used for storage of operation-attached artifacts

    TODO: Deprecate when possible, will require a migration
    """

    URN_PREFIX: ClassVar = "urn:x-mfg:transform"

    kind_urn: str
    input_artifacts: Optional[List[DbId]]
    output_artifacts: Optional[List[DbId]]
    parameters: Any


#
# Attachment Graphs for Operations
#


class AttachmentMode(enum.Enum):
    INPUT = "input"
    OUTPUT = "output"


class AttachmentRelation(enum.Enum):
    CHILD = "child"
    MATERIAL_TRANSFORM = "material_transform"
    MEASUREMENT = "measurement"


class AttachmentGraph(networkx.MultiDiGraph):

    """
    An attachment graph is a tree of attached artifacts, and can be explored via the standard
    networkx graph operations.
    """

    class AttachmentNode(BaseJsonModel):

        kind_path: Tuple[str, ...]
        artifact_id: Optional[str]
        attachment_mode: AttachmentMode

        @staticmethod
        def build(kind_path, artifact_id, attachment_mode):
            return AttachmentGraph.AttachmentNode(
                kind_path=tuple(map(str, kind_path)),
                artifact_id=str(artifact_id) if artifact_id is not None else None,
                attachment_mode=(
                    attachment_mode
                    if isinstance(attachment_mode, AttachmentMode)
                    else AttachmentMode(attachment_mode)
                ),
            )

        @property
        def artifact_path(self):
            return (
                ".".join(list(self.kind_path) + [self.artifact_id])
                if self.kind_path
                else ""
            )

        def __members(self):
            return (self.kind_path, self.artifact_id, self.attachment_mode)

        def __eq__(self, other):
            if type(other) is type(self):
                return self.__members() == other.__members()
            else:
                return False

        def __hash__(self):
            return hash(self.__members())

        def __repr__(self):
            return f"{type(self).__name__}{self.__members()}"

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

    def from_artifact_transform_list(self, transforms: List[ArtifactTransform]):

        self.root = AttachmentGraph.AttachmentNode.build(
            [], None, AttachmentMode.OUTPUT
        )

        self.add_node(self.root)
        parents = {tuple([]): self.root}

        def transforms_to_nodes(
            transforms: List[ArtifactTransform],
        ) -> Sequence[AttachmentGraph.AttachmentNode]:

            for transform in transforms:
                kind_path = tuple(transform.kind_urn.split("."))
                for input_id in transform.input_artifacts or []:
                    yield AttachmentGraph.AttachmentNode.build(
                        kind_path, input_id, AttachmentMode.INPUT
                    )
                for output_id in transform.output_artifacts or []:
                    yield AttachmentGraph.AttachmentNode.build(
                        kind_path, output_id, AttachmentMode.OUTPUT
                    )

        for node in sorted(
            list(transforms_to_nodes(transforms)), key=lambda a: a.kind_path
        ):

            self.add_node(node)

            parent = parents.get(node.kind_path[:-1])

            if parent is not None:
                self.add_relation(parent, node, AttachmentRelation.CHILD)
            else:
                logger.warn(
                    f"Parent attachment not found for attachment at {node.artifact_path}, attachment is orphaned in the parent operation"
                )

            parents[tuple(list(node.kind_path) + [str(node.artifact_id)])] = node

        return self

    def to_artifact_transform_list(self) -> List[ArtifactTransform]:

        kind_path_transforms = {}

        for node in self.nodes():
            if node == self.root:
                continue

            transform: ArtifactTransform = kind_path_transforms.setdefault(
                node.kind_path,
                ArtifactTransform(
                    kind_urn=".".join(node.kind_path),
                    input_artifacts=[],
                    output_artifacts=[],
                ),
            )

            (
                transform.input_artifacts
                if node.attachment_mode == AttachmentMode.INPUT
                else transform.output_artifacts
            ).append(DbId.init(node.artifact_id))

        transforms = sorted(
            list(kind_path_transforms.values()), key=lambda t: t.kind_urn
        )

        return transforms

    def add_attachment_node(self, node: AttachmentNode):
        self.add_node(node)
        return node

    def build_attachment_node(
        self, kind_path: List, artifact_id, attachment_mode: AttachmentMode
    ):
        return self.add_attachment_node(
            AttachmentGraph.AttachmentNode.build(
                kind_path, artifact_id, attachment_mode
            )
        )

    def remove_attachment_node_and_descendants(self, node: AttachmentNode):
        for descendant_node in networkx.algorithms.descendants(self, node):
            self.remove_node(descendant_node)
        self.remove_node(node)

    def replace_attachment_node(self, old_node, new_node):

        if old_node not in self.nodes() or new_node.__eq__(old_node):
            return

        self.add_attachment_node(new_node)
        for node_from, _, relation in self.in_edges(old_node, keys=True):
            self.add_edge(node_from, new_node, relation)
        for _, node_to, relation in self.out_edges(old_node, keys=True):
            self.add_edge(new_node, node_to, relation)
        self.remove_node(old_node)

    def add_relation(self, node_from, node_to, relation: AttachmentRelation):
        return self.add_edge(node_from, node_to, relation)

    def parent(self, node: AttachmentNode) -> Optional[AttachmentNode]:
        for node_from, _, relation in self.in_edges(node, keys=True):
            if relation == AttachmentRelation.CHILD:
                return node_from
        return None

    def childen(self, node: AttachmentNode) -> List[AttachmentNode]:
        children = []
        for _, node_to, relation in self.out_edges(node, keys=True):
            if relation == AttachmentRelation.CHILD:
                children.append(node_to)
        return children

    #
    # Attachment Queries
    #

    def find_nodes(
        self,
        kind_path: List = None,
        artifact_id=None,
        attachment_mode: AttachmentMode = None,
        parent_artifact_path: List = None,
    ) -> Sequence[AttachmentNode]:

        if artifact_id is not None:
            artifact_id = str(artifact_id)
        if kind_path is not None:
            kind_path = tuple(map(str, kind_path))
        if parent_artifact_path is not None:
            parent_artifact_path = tuple(map(str, parent_artifact_path))

        for node in self.nodes:
            if (
                (artifact_id is None or str(node.artifact_id) == artifact_id)
                and (kind_path is None or node.kind_path == kind_path)
                and (attachment_mode is None or node.attachment_mode == attachment_mode)
                and (
                    parent_artifact_path is None
                    or (node.kind_path and node.kind_path[0:-1] == parent_artifact_path)
                )
            ):
                yield node

    def find_node(self, *args, **kwargs):
        return (list(self.find_nodes(*args, **kwargs)) or [None])[0]

    def find_nodes_by_artifact(
        self, artifact_id, attachment_mode=None
    ) -> Sequence[AttachmentNode]:
        return self.find_nodes(artifact_id=artifact_id, attachment_mode=attachment_mode)

    def find_node_by_artifact(self, *args, **kwargs) -> AttachmentNode:
        return (list(self.find_nodes_by_artifact(*args, **kwargs)) or [None])[0]

    def find_nodes_by_path(self, kind_path) -> Sequence[AttachmentNode]:
        return self.find_nodes(kind_path=kind_path)

    def find_node_by_path(self, *args, **kwargs) -> AttachmentNode:
        return (list(self.find_nodes_by_path(*args, **kwargs)) or [None])[0]

    def _artifact_path_expr_to_re(self, path_expr: str, context: AttachmentNode = None):

        path_root = None
        while path_expr.startswith("."):

            if path_root is None:
                # Start at the context node for relative paths
                path_root = context
            else:
                # Move up one node each "."
                prev_context = (list(self.predecessors(path_root)) or [None])[0]

            # Abort if we've gone too far
            if path_root is None:
                return None

            path_expr = path_expr[1:]

        re_prefix = None

        path_res = []
        for split_expr in path_expr.split(".") if path_expr else []:

            if split_expr == "*":
                path_res.append("[^\\.]+")
            elif split_expr == "**":
                path_res.append(".+")
            else:
                path_res.append(re.escape(split_expr))

        if path_root is not None:
            re_prefix = re.escape(path_root.artifact_path)
            path_res = [re_prefix] + path_res

        path_re = "^" + "\\.".join(path_res) + "$"
        return path_re

    def find_nodes_by_artifact_path_expr(
        self, path_expr: str, context: AttachmentNode = None
    ) -> Sequence[AttachmentNode]:

        path_re = self._artifact_path_expr_to_re(path_expr, context)
        path_re = re.compile(path_re)

        for node in self.nodes:
            if re.match(path_re, node.artifact_path):
                yield node

    def find_node_by_artifact_path_expr(self, *args, **kwargs):
        return (list(self.find_nodes_by_artifact_path_expr(*args, **kwargs)) or [None])[
            0
        ]


class Operation(DocModel):

    URN_PREFIX: ClassVar = "urn:x-mfg:operation"

    # Keep these required for later use in sharding and vfs interfaces
    type_urn: str
    project: DbId

    name: Optional[str]
    description: Optional[str]
    tags: Optional[List[str]]
    active: bool = True

    system_name: Optional[str]
    system_id: Optional[DbId]
    human_operator_names: Optional[List[str]]
    human_operator_ids: Optional[List[DbId]]

    start_at: Optional[datetime.datetime]
    end_at: Optional[datetime.datetime]
    status: Optional[str]

    # DRAGONS DRAGONS DRAGONS
    # The "ArtifactTransform" must be listed *first* in order for parsing to
    # pick it up correctly
    artifact_transform_graph: Union[Optional[List[ArtifactTransform]], Any]

    # DRAGONS DRAGONS DRAGONS
    # We *immediately*, after parsing, convert the ArtifactTransforms into
    # an AttachmentGraph because attachments are way simpler to manage this
    # way.  On the way back to JSON we re-serialize as ArtifactTransforms
    # (until we migrate data and remove ArtifactTransform as a model, though
    # there will always need to be a JSON representation of the graph).

    @property
    def attachments(self) -> AttachmentGraph:
        return self.artifact_transform_graph

    @pydantic.root_validator
    def validate_attachment_graph(cls, values):
        values[
            "artifact_transform_graph"
        ] = AttachmentGraph().from_artifact_transform_list(
            values["artifact_transform_graph"] or []
        )
        return values

    def dict(self, *args, **kwargs):
        values = super().dict(*args, **kwargs)
        if "artifact_transform_graph" in values and isinstance(
            values["artifact_transform_graph"], AttachmentGraph
        ):
            values["artifact_transform_graph"] = list(
                map(
                    lambda t: t.dict(),
                    values["artifact_transform_graph"].to_artifact_transform_list(),
                )
            )
        return values

    class Config(pydantic.BaseConfig):
        arbitrary_types_allowed = True


class StoredSchema(DocModel):

    type_urn: str
    project: Optional[DbId]
    module: Optional[str]
    tags: Optional[List[str]]
    active: bool = True

    storage_schema_json: Optional[str]
    storage_schema_hash: Optional[str]

    storage_schema_yaml: Optional[str]
    storage_schema_json5: Optional[str]

    @pydantic.root_validator
    def validate_storage_schemas(cls, values):
        if values.get("storage_schema_json", None) is None:
            if values.get("storage_schema_json5", None) is not None:
                import pyjson5

                values["storage_schema_json"] = json.dumps(
                    pyjson5.loads(values["storage_schema_json5"])
                )
            elif values.get("storage_schema_yaml", None) is not None:
                import yaml

                values["storage_schema_json"] = json.dumps(
                    yaml.load(values["storage_schema_yaml"])
                )
        if values.get("storage_schema_hash", None) is None:

            if values.get("storage_schema_json", None) is None:
                raise Exception(
                    f"Cannot hash missing storage schema for type {values.get('type_urn')}"
                )

            hasher = hashlib.sha256()
            hasher.update(values["storage_schema_json"].encode("utf-8"))
            values["storage_schema_hash"] = f"sha256:{hasher.hexdigest()}"
        return values

    def storage_schema_type_urn(self):
        return json.loads(self.storage_schema_json).get("type_urn")
