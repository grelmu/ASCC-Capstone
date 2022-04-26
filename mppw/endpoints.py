import pydantic
import typing
from typing import List, Tuple, Union

from . import models
from .services.provenance_services import ProvenanceStepGraph

class Change(pydantic.BaseModel):
    op: str
    path: str
    value: typing.Optional[typing.Any]

ProvenanceNode = Union[ProvenanceStepGraph.ArtifactNode, ProvenanceStepGraph.OperationStepNode]

class ProvenanceGraphModel(pydantic.BaseModel):
    nodes: List[ProvenanceNode]
    edges: List[Tuple[ProvenanceNode, ProvenanceNode, models.AttachmentGraph.AttachmentNode]]

    def from_graph(provenance: ProvenanceStepGraph):

        model = ProvenanceGraphModel(nodes=[], edges=[])

        for node in provenance.nodes():
            model.nodes.append(node)

        for edge in provenance.edges(keys=True):
            model.edges.append(tuple(edge))

        return model