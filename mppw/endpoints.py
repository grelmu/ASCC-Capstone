import pydantic
import typing

class Change(pydantic.BaseModel):
    op: str
    path: str
    value: typing.Optional[typing.Any]