import pydantic
import typing
from typing import List, Tuple, Union, Any

from . import models
from .services.provenance_services import ArtifactFrameGraph, ProvenanceStepGraph


class Change(pydantic.BaseModel):
    op: str
    path: str
    value: typing.Optional[typing.Any]


#
# Serialization to pydantic / JSON of ProvenanceGraphs
#

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


#
# Serialization to pydantic/JSON of ArtifactFrameGraphs
#


class ArtifactFrameGraphEdgeModel(models.BaseJsonModel):
    from_node: ArtifactFrameGraph.ArtifactNode
    to_node: ArtifactFrameGraph.ArtifactNode
    data: Any


class ArtifactFrameGraphModel(models.BaseJsonModel):

    nodes: List[ArtifactFrameGraph.ArtifactNode]
    edges: List[ArtifactFrameGraphEdgeModel]

    def from_graph(frame_graph: ArtifactFrameGraph):

        model = ProvenanceGraphModel(nodes=[], edges=[])

        for node in frame_graph.nodes():
            model.nodes.append(node)

        for from_node, to_node, data in frame_graph.edges(data=True):
            model.edges.append(
                ArtifactFrameGraphEdgeModel(
                    from_node=from_node, to_node=to_node, data=data
                )
            )

        return model
