import fastapi
import fastapi.encoders
import asyncio
import pydantic
import json_stream
import typing
from typing import List, Tuple, Union, Any

from . import models
from .services.provenance_services import (
    ArtifactFrameGraph,
    ArtifactFramePath,
    ProvenanceStepGraph,
    ProvenanceStepPath,
)


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


class ProvenanceEdgeModel(models.BaseJsonModel):
    from_node: ProvenanceNode
    to_node: ProvenanceNode
    key: Any


class ProvenanceGraphModel(pydantic.BaseModel):
    nodes: List[ProvenanceNode]
    edges: List[ProvenanceEdgeModel]

    def from_graph(provenance: typing.Optional[ProvenanceStepGraph]):
        if provenance is None:
            return None

        model = ProvenanceGraphModel(nodes=[], edges=[])

        for node in provenance.nodes():
            model.nodes.append(node)

        for from_node, to_node, key in provenance.edges(keys=True):
            model.edges.append(
                ProvenanceEdgeModel(from_node=from_node, to_node=to_node, key=key)
            )

        return model

    @staticmethod
    def cypher_node_results_model(
        cypher_node_results: dict, graph: ProvenanceStepGraph
    ) -> typing.Dict[str, List[ProvenanceNode]]:
        results_model = dict()

        for name, node_results in cypher_node_results.items():
            results_model[str(name)] = nodes_model = []
            for node in node_results:
                nodes_model.append(node)

        return results_model


class ProvenancePathModel(models.BaseJsonModel):
    path_nodes: List[ProvenanceNode]
    path_edges: List[ProvenanceEdgeModel]

    @staticmethod
    def from_path(provenance_path: ProvenanceStepPath):
        if provenance_path is None:
            return None

        return ProvenancePathModel(
            path_nodes=list(provenance_path.path_nodes),
            path_edges=[
                ProvenanceEdgeModel(
                    from_node=from_node, to_node=to_node, key=data["key"]
                )
                for from_node, to_node, data in provenance_path.path_edges
            ],
        )


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

    def from_graph(frame_graph: typing.Optional[ArtifactFrameGraph]):
        if frame_graph is None:
            return None

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


class ArtifactFramePathModel(models.BaseJsonModel):
    path_nodes: List[ArtifactFrameGraph.ArtifactNode]
    path_edges: List[ArtifactFrameGraphEdgeModel]

    def from_path(frame_path: typing.Optional[ArtifactFramePath]):
        if frame_path is None:
            return None

        model = ArtifactFramePathModel(
            path_nodes=list(frame_path.path_nodes), path_edges=[]
        )

        for from_node, to_node, data in frame_path.path_edges:
            model.path_edges.append(
                ArtifactFrameGraphEdgeModel(
                    from_node=from_node, to_node=to_node, data=data
                )
            )

        return model


class RelatedFramePathModel(models.BaseJsonModel):
    provenance_path: ProvenancePathModel
    frame_path: ArtifactFramePathModel

    @staticmethod
    def from_paths(provenance_path: ProvenanceStepPath, frame_path: ArtifactFramePath):
        return RelatedFramePathModel(
            provenance_path=ProvenancePathModel.from_path(provenance_path),
            frame_path=ArtifactFramePathModel.from_path(frame_path),
        )


async def sync_body_stream(request: fastapi.Request):
    """
    Creates a synchronous generator that produces request body data from the
    standard FastAPI/Starlette async version.

    DRAGONS: While the sync API call runs in a thread pool, the async generator
    reads data from a separate async loop thread/pool.  These may not be the
    same thread pools.

    Usage: parameter = Depends(sync_body_stream)
    """

    main_loop = asyncio.get_running_loop()
    stream = request.stream()

    # Backward compatible sync generator
    def gen_from_async_loop():
        try:
            while True:
                future = asyncio.run_coroutine_threadsafe(stream.__anext__(), main_loop)
                yield future.result(None)
        except StopAsyncIteration:
            return

    return gen_from_async_loop()


def json_string_gen_to_json_values_gen(json_string_gen):
    return (stream_json_to_value(p) for p in json_stream.load(json_string_gen))


def stream_json_to_value(maybe_value):
    if isinstance(maybe_value, json_stream.base.StreamingJSONObject):
        return dict((k, stream_json_to_value(v)) for k, v in maybe_value.items())
    elif isinstance(maybe_value, json_stream.base.StreamingJSONList):
        return list(stream_json_to_value(v) for v in maybe_value)
    return maybe_value


class StreamingJsonResponse(fastapi.responses.StreamingResponse):
    @staticmethod
    def gen_to_json_bytes_gen(gen):
        renderer = fastapi.responses.JSONResponse()

        yield "[".encode("utf-8")

        try:
            i = 0
            while True:
                next_bytes = renderer.render(
                    fastapi.encoders.jsonable_encoder(next(gen))
                )
                if i > 0:
                    next_bytes = ",".encode("utf-8") + next_bytes
                yield next_bytes
                i += 1

        except StopIteration:
            pass

        yield "]".encode("utf-8")

    def __init__(self, gen, *args, **kwargs):
        bytes_gen = StreamingJsonResponse.gen_to_json_bytes_gen(gen)
        super().__init__(
            bytes_gen,
            media_type=fastapi.responses.JSONResponse.media_type,
            *args,
            **kwargs
        )
