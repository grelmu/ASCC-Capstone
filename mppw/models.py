from typing import Optional, List, ClassVar, Any, Union, Dict
import fastapi
import fastapi.encoders
import pydantic
import bson
import datetime

from mppw import logger

class PyObjectId(bson.ObjectId):

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not bson.ObjectId.is_valid(v):
            raise ValueError('Invalid objectid')
        return bson.ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type='string')
  
class ConfigKv(pydantic.BaseModel):
    key: str
    value: Optional[str]

class DocModel(pydantic.BaseModel):

    id: Optional[Union[PyObjectId, str]]

    class Config(pydantic.BaseConfig):
        json_encoders = {
            datetime.datetime: lambda dt: dt.isoformat(),
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
    project: Union[PyObjectId, str]

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

class ArtifactTransform(pydantic.BaseModel):

    URN_PREFIX: ClassVar = "urn:x-mfg:transform"

    kind_urn: str
    input_artifacts: Optional[List[Union[PyObjectId, str]]]
    output_artifacts: Optional[List[Union[PyObjectId, str]]]
    parameters: Any
    
class Operation(DocModel):

    URN_PREFIX: ClassVar = "urn:x-mfg:operation"

    # Keep these required for later use in sharding and vfs interfaces
    type_urn: str
    project: Union[PyObjectId, str]

    name: Optional[str]
    description: Optional[str]
    tags: Optional[List[str]]
    active: bool = True

    system_name: Optional[str]
    system_id: Optional[Union[PyObjectId, str]]
    human_operator_names: Optional[List[str]]
    human_operator_ids: Optional[List[Union[PyObjectId, str]]]

    start_at: Optional[datetime.datetime]
    end_at: Optional[datetime.datetime]
    status: Optional[str]

    artifact_transform_graph: Optional[List[ArtifactTransform]]

    @pydantic.validator("type_urn")
    def valid_type_urn_prefix(cls, v):
        if not v.startswith(Operation.URN_PREFIX):
            raise ValueError(f"operation URNs must start with {Operation.URN_PREFIX}: {v}")
        return v

