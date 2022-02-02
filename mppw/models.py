from typing import Optional, List, ClassVar, Any, Union, Dict
import fastapi
import fastapi.encoders
import pydantic
import bson
import datetime

from mppw import logger

class DbId:

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, val):
        if isinstance(val, DbId): return val
        if isinstance(val, bson.ObjectId): return ObjectDbId(val)
        if isinstance(val, str):
            try:
                return ObjectDbId(bson.ObjectId(val))
            except:
                return StrDbId(val)
        else:
            raise Exception(f"Unknown db id value of {val}")

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type='string')

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
  
class ConfigKv(pydantic.BaseModel):
    key: str
    value: Optional[str]

class DocModel(pydantic.BaseModel):

    id: Optional[DbId]

    class Config(pydantic.BaseConfig):
        json_encoders = {
            datetime.datetime: lambda dt: dt.isoformat(),
            ObjectDbId: lambda dbid: dbid.__json__(),
            StrDbId: lambda dbid: dbid.__json__(),
            bson.ObjectId: lambda oid: str(oid),
        }

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

class Project(DocModel):
    name: str
    description: Optional[str]
    active: bool = True

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

    label: str
    geometry_labels: List[GeometryLabel]
    location_label: Optional[str]

    @pydantic.validator("type_urn")
    def valid_type_urn_prefix(cls, v):
        if not v.startswith(MaterialArtifact.URN_PREFIX):
            raise ValueError(f"material artifact URNs must start with {MaterialArtifact.URN_PREFIX}: {v}")
        return v

class DigitalArtifact(Artifact):

    URN_PREFIX: ClassVar = f"{Artifact.URN_PREFIX}:digital"

    local_data: Any
    url_data: Optional[str]

    @pydantic.validator("type_urn")
    def valid_type_urn_prefix(cls, v):
        if not v.startswith(DigitalArtifact.URN_PREFIX):
            raise ValueError(f"digital artifact URNs must start with {DigitalArtifact.URN_PREFIX}: {v}")
        return v

AnyArtifact = Union[MaterialArtifact, DigitalArtifact]

class ArtifactTransform(pydantic.BaseModel):

    URN_PREFIX: ClassVar = "urn:x-mfg:transform"

    kind_urn: str
    input_artifacts: Optional[List[DbId]]
    output_artifacts: Optional[List[DbId]]
    parameters: Any
    
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

    artifact_transform_graph: Optional[List[ArtifactTransform]]

    @pydantic.validator("type_urn")
    def valid_type_urn_prefix(cls, v):
        if not v.startswith(Operation.URN_PREFIX):
            raise ValueError(f"operation URNs must start with {Operation.URN_PREFIX}: {v}")
        return v