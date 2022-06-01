import enum
from lib2to3.pgen2.grammar import opmap_raw
import pydantic
import networkx
import json
import re
from typing import List, Set, Sequence, Optional

from .. import repositories
from .. import models
from .. import schemas

"""
Services that allow the building and exploration of provenance graphs.
"""


class ProvenanceStepGraph(networkx.MultiDiGraph):

    """
    A bipartite graph representation of a process provenance

    The graph consists of artifacts linked by operation steps - artifacts are input and output from
    each operation step and then linked to other operation steps.
    """

    # NOTE that these nodes must support equality comparisons
    class ArtifactNode(pydantic.BaseModel):

        artifact_id: str

        def __members(self):
            return (self.artifact_id,)

        def __eq__(self, other):
            if type(other) is type(self):
                return self.__members() == other.__members()
            else:
                return False

        def __hash__(self):
            return hash(self.__members())

    class OperationStepNode(pydantic.BaseModel):

        operation_id: str
        context_path: str
        name: str

        def __members(self):
            return (self.operation_id, self.context_path, self.name)

        def __eq__(self, other):
            if type(other) is type(self):
                return self.__members() == other.__members()
            else:
                return False

        def __hash__(self):
            return hash(self.__members())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def build_from_operation(self, operation: models.Operation):

        """
        Every operation with attachments can be transformed into a linked provenance graph
        of operation steps.

        The operation schema is used to define how attachments are related to the operation
        steps and whether they are input or output.  The attachment nodes, which include the
        attachment "kind" names, are the metadata keys of each edge between an artifact and
        an operation step.  Essentially this "names" each input and output of the operation
        steps in an operation-type-dependent way, which preserves the maximum information
        about how the artifacts are used as input or output in the step.
        """

        provenance_schema = schemas.get_operation_schema(operation.type_urn).provenance

        for step_def in provenance_schema.steps:

            context_nodes = [operation.attachments.root]
            if step_def.context is not None:
                context_nodes = operation.attachments.find_nodes_by_artifact_path_expr(
                    step_def.context
                )

            for context_node in context_nodes:

                step_node = ProvenanceStepGraph.OperationStepNode(
                    operation_id=str(operation.id),
                    context_path=context_node.artifact_path,
                    name=step_def.name or ":default",
                )

                from_edges = []
                for expr in step_def.from_artifacts:
                    for (
                        node_from
                    ) in operation.attachments.find_nodes_by_artifact_path_expr(
                        expr, context_node
                    ):
                        artifact_node = ProvenanceStepGraph.ArtifactNode(
                            artifact_id=node_from.artifact_id
                        )
                        from_edges.append((artifact_node, step_node, node_from))

                if not (
                    from_edges or step_def.is_source or step_node.name == ":default"
                ):
                    continue

                to_edges = []
                for expr in step_def.to_artifacts:
                    for (
                        node_to
                    ) in operation.attachments.find_nodes_by_artifact_path_expr(
                        expr, context_node
                    ):
                        artifact_node = ProvenanceStepGraph.ArtifactNode(
                            artifact_id=node_to.artifact_id
                        )

                        # NOTE that we are preserving *all* of the attachment information by using the
                        # attachment node "node_to" as the key of the edge
                        to_edges.append((step_node, artifact_node, node_to))

                if not (to_edges or step_def.is_sink or step_node.name == ":default"):
                    continue

                for edges in [from_edges, to_edges]:
                    for edge in edges:
                        self.add_edge(*edge)

        return self

    def extend_with_operation(
        self,
        operation: models.Operation,
        artifact_node: ArtifactNode,
        strategy: str = None,
        cache={},
    ):

        """
        Adds relevant steps from an operation to an existing process provenance, starting at
        a particular artifact.

        The overall approach is to build the operation subgraph, explore starting from the artifact
        in the subgraph (using a given exploration strategy), and then overlay/combine the resulting
        subgraph onto the current graph.  The additional nodes and edges are returned.
        """

        if strategy is None:
            strategy = "ancestors"

        operation_provenance: ProvenanceStepGraph = cache.get(operation.id)
        if operation_provenance is None:
            operation_provenance = ProvenanceStepGraph().build_from_operation(operation)
            cache[operation.id] = operation_provenance

        if artifact_node not in operation_provenance.nodes():
            return ProvenanceStepGraph()

        if strategy.startswith("ancestors"):
            extended_provenance: ProvenanceStepGraph = operation_provenance.subgraph(
                [artifact_node]
                + list(
                    networkx.algorithms.ancestors(operation_provenance, artifact_node)
                )
            )

        if strategy.startswith("descendants"):
            extended_provenance: ProvenanceStepGraph = operation_provenance.subgraph(
                [artifact_node]
                + list(
                    networkx.algorithms.descendants(operation_provenance, artifact_node)
                )
            )

        self.add_edges_from(extended_provenance.edges(keys=True, data=True))

        # A strategy may include a "radius", which allows us to search outward a configurable
        # number of nodes from every related artifact in the filtered subgraph.  A major use
        # is to find the ancestors of an artifact along with any measurements done to those
        # ancestors.
        radius_split = strategy.split("+")
        radius = 0
        if len(radius_split) == 2:
            radius = int(radius_split[1])

        if radius > 0:

            for ext_artifact_node in filter(
                lambda n: isinstance(n, ProvenanceStepGraph.ArtifactNode),
                extended_provenance.nodes(),
            ):
                bfs_provenance = operation_provenance.subgraph(
                    networkx.algorithms.bfs_tree(
                        operation_provenance,
                        ext_artifact_node,
                        depth_limit=radius,
                        reverse=strategy.startswith("descendants"),
                    ).nodes()
                )

                self.add_edges_from(bfs_provenance.edges(keys=True, data=True))

        return extended_provenance

    def artifact_nodes(self):
        return filter(
            lambda n: isinstance(n, ProvenanceStepGraph.ArtifactNode), self.nodes()
        )

    def step_nodes(self):
        return filter(
            lambda n: isinstance(n, ProvenanceStepGraph.OperationStepNode), self.nodes()
        )

    def __human_str__(self, repo_layer=None):
        builder = []
        builder.append("Nodes:")
        for node in self.nodes():
            builder.append("  " + node.__repr__())
            if repo_layer:

                if isinstance(node, ProvenanceStepGraph.ArtifactNode):
                    artifact = repo_layer.artifacts.query_one(id=node.artifact_id)
                    builder.append("    " + f"{artifact.type_urn} {artifact.name}")

                elif isinstance(node, ProvenanceStepGraph.OperationStepNode):
                    operation = repo_layer.operations.query_one(id=node.operation_id)
                    builder.append("    " + f"{operation.type_urn} {operation.name}")

        builder.append("Edges:")
        for edge in self.edges(keys=True):
            builder.append("  " + edge.__repr__())
        return "\n".join(builder)


class ArtifactFrameGraph(networkx.DiGraph):

    """
    A graph representation of spatial frames - aka how artifacts are spatially related to each other

    The graph consists of digital artifacts linked by spatial transforms - transforms map the coordinate
    systems of one artifact to another.  Each edge between artifacts is associated with a spatial frame.
    """

    # NOTE that these nodes must support equality comparisons
    class ArtifactNode(pydantic.BaseModel):

        artifact_id: str

        def __members(self):
            return (self.artifact_id,)

        def __eq__(self, other):
            if type(other) is type(self):
                return self.__members() == other.__members()
            else:
                return False

        def __hash__(self):
            return hash(self.__members())

    def add_spatial_artifact(self, artifact: models.DigitalArtifact):

        child_node = ArtifactFrameGraph.ArtifactNode(artifact_id=str(artifact.id))

        if not artifact.spatial_frame or not artifact.spatial_frame.parent_frame:
            return (None, None, None)

        parent_node = ArtifactFrameGraph.ArtifactNode(
            artifact_id=str(artifact.spatial_frame.parent_frame)
        )

        self.add_edge(parent_node, child_node, frame=artifact.spatial_frame)
        return (parent_node, child_node, self.edges[parent_node, child_node])

    def __human_str__(self, repo_layer=None):
        builder = []
        builder.append("Nodes:")
        for node in self.nodes():
            builder.append("  " + node.__repr__())
            if repo_layer:
                artifact = repo_layer.artifacts.query_one(id=node.artifact_id)
                builder.append("    " + f"{artifact.type_urn} {artifact.name}")

        builder.append("Edges:")
        for edge in self.edges(data=True):
            builder.append("  " + edge.__repr__())
        return "\n".join(builder)


class ProvenanceServices:

    """
    Services related to exploring the provenance of artifacts and operations
    """

    def __init__(self, service_layer):

        from .service_layer import ServiceLayer

        self.service_layer: ServiceLayer = service_layer
        self.repo_layer = self.service_layer.repo_layer

    def build_operation_steps(self, operation) -> ProvenanceStepGraph:

        """
        Build the operation steps and artifact relationships for a single operation
        """

        return ProvenanceStepGraph().build_from_operation(operation)

    def build_artifact_provenance(
        self, artifact_id, strategy: str = None
    ) -> ProvenanceStepGraph:

        """
        Grow a provenance starting from a particular artifact.

        The exact exploration strategy is configurable to "ancestors" and "descendants(+r) -
        in either case, the exploration proceeds by:
          - finding all operations with the artifact attached
          - overlaying the relevant subgraphs generated by those operations onto the growing provenance
          - finding unexplored artifacts from the operation step subgraphs to explore next
          - continue until all seen artifacts are explored
        """

        provenance_graph = ProvenanceStepGraph()
        seed_node = ProvenanceStepGraph.ArtifactNode(artifact_id=str(artifact_id))
        fringe: List[ProvenanceStepGraph.ArtifactNode] = [seed_node]
        seen_artifact_nodes: Set[ProvenanceStepGraph.ArtifactNode] = set(fringe)

        operations_repo: repositories.OperationRepository = self.repo_layer.operations

        while fringe:

            next_artifact_node = fringe.pop()

            artifact_operations = operations_repo.query_by_attached(
                artifact_id=next_artifact_node.artifact_id
            )

            for operation in artifact_operations:

                extended_provenance = provenance_graph.extend_with_operation(
                    operation, next_artifact_node, strategy=strategy
                )

                for artifact_node in extended_provenance.nodes():

                    if not isinstance(artifact_node, ProvenanceStepGraph.ArtifactNode):
                        continue

                    if artifact_node not in seen_artifact_nodes:
                        fringe.append(artifact_node)
                        seen_artifact_nodes.add(artifact_node)

        return provenance_graph

    def build_artifact_frame_graph(self, artifact_id, strategy: str = None):

        """
        Grow a frame graph starting from a particular artifact.

        The exact exploration strategy is configurable to "full", "parents", and "children".

        The exploration proceeds by:
          - finding all frame parents and/or children of the current artifact node
            - parents are artifacts that are spatial_frame.parent_frames of the current artifact
            - children are artifacts that reference the current artifact in their spatial_frame.parent_frame
          - adding the parent and/or children edges (and nodes, implicitly) to the growing graph
          - finding unexplored parent/children from above to explore next
          - continue until all seen artifacts are explored
        """

        if strategy is None:
            strategy = "full"

        frame_graph = ArtifactFrameGraph()
        seed_node = ArtifactFrameGraph.ArtifactNode(artifact_id=str(artifact_id))
        fringe: List[ArtifactFrameGraph.ArtifactNode] = [seed_node]
        seen_artifact_nodes: Set[ArtifactFrameGraph.ArtifactNode] = set(fringe)

        artifacts_repo: repositories.ArtifactRepository = self.repo_layer.artifacts

        while fringe:

            next_artifact_node = fringe.pop()

            related_artifacts: List[models.DigitalArtifact] = []
            if strategy == "full" or strategy == "parents":
                related_artifacts.extend(
                    [artifacts_repo.query_one(next_artifact_node.artifact_id)]
                )

            if strategy == "full" or strategy == "children":
                related_artifacts.extend(
                    list(
                        artifacts_repo.query(
                            parent_frame_id=next_artifact_node.artifact_id
                        ),
                    )
                )

            for related_artifact in related_artifacts:
                parent_node, child_node, _ = frame_graph.add_spatial_artifact(
                    related_artifact
                )
                for new_node in [parent_node, child_node]:
                    if new_node is not None and new_node not in seen_artifact_nodes:
                        seen_artifact_nodes.add(new_node)
                        fringe.append(new_node)

        return frame_graph
