import pydantic
import typing
from typing import List, Tuple, Union, Any

from . import models
from .services.provenance_services import ProvenanceStepGraph


class Change(pydantic.BaseModel):
    op: str
    path: str
    value: typing.Optional[typing.Any]


ProvenanceNode = Union[
    ProvenanceStepGraph.ArtifactNode, ProvenanceStepGraph.OperationStepNode
]


class ProvenanceEdgeModel(pydantic.BaseModel):
    from_node: ProvenanceNode
    to_node: ProvenanceNode
    key: Any


class ProvenanceGraphModel(pydantic.BaseModel):

    nodes: List[ProvenanceNode]
    edges: List[ProvenanceEdgeModel]

    def from_graph(provenance: ProvenanceStepGraph):

        model = ProvenanceGraphModel(nodes=[], edges=[])

        for node in provenance.nodes():
            model.nodes.append(node)

        for from_node, to_node, key in provenance.edges(keys=True):
            model.edges.append(
                ProvenanceEdgeModel(from_node=from_node, to_node=to_node, key=key)
            )

        return model
