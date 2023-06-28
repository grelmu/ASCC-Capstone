import enum
import pydantic
import networkx
import json
import re
from typing import List, Set, Sequence, Optional
import grandcypher

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

    def build_from_operation(
        self,
        operation: models.Operation,
        schema: schemas.OperationSchema,
        include_motif_attrs=False,
        artifact_cb=None,
    ):
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

        provenance_schema = schema.provenance

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

                if (from_edges or to_edges) and include_motif_attrs:
                    self.add_node(
                        step_node,
                        __labels__=set(
                            [ProvenanceStepGraph.OperationStepNode.__name__]
                        ),
                        node_type=ProvenanceStepGraph.OperationStepNode.__name__,
                        type_urn=operation.type_urn,
                        step_name=step_node.name,
                        #
                        tags=operation.tags,
                    )

                    for edges in [from_edges, to_edges]:
                        for node_from, node_to, _ in edges:
                            artifact_node = (
                                node_from
                                if isinstance(
                                    node_from, ProvenanceStepGraph.ArtifactNode
                                )
                                else node_to
                            )

                            artifact = artifact_cb(artifact_node.artifact_id)

                            if isinstance(artifact, models.MaterialArtifact):
                                self.add_node(
                                    artifact_node,
                                    __labels__=set(
                                        [ProvenanceStepGraph.ArtifactNode.__name__]
                                    ),
                                    node_type=ProvenanceStepGraph.ArtifactNode.__name__,
                                    type_urn=artifact.type_urn,
                                    #
                                    tags=artifact.tags,
                                    #
                                    material_system_urn=artifact.material_system_urn,
                                    label=artifact.label,
                                )
                            elif isinstance(artifact, models.DigitalArtifact):
                                self.add_node(
                                    artifact_node,
                                    __labels__=set(
                                        [ProvenanceStepGraph.ArtifactNode.__name__]
                                    ),
                                    node_type=ProvenanceStepGraph.ArtifactNode.__name__,
                                    type_urn=artifact.type_urn,
                                    #
                                    tags=artifact.tags,
                                    #
                                    local_data=artifact.local_data,
                                    url_data=artifact.url_data,
                                )

                    for _, artifact_node, _ in to_edges:
                        pass

                for edges in [from_edges, to_edges]:
                    for edge in edges:
                        self.add_edge(*edge)

        return self

    def extend_with_operation(
        self,
        operation: models.Operation,
        schema_cb,
        artifact_node: ArtifactNode,
        strategy: str = None,
        include_motif_attrs=False,
        artifact_cb=None,
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
            operation_provenance = ProvenanceStepGraph().build_from_operation(
                operation,
                schema_cb(),
                include_motif_attrs=include_motif_attrs,
                artifact_cb=artifact_cb,
            )
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

        self.add_nodes_from(extended_provenance.nodes(data=True))
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

                self.add_nodes_from(bfs_provenance.nodes(data=True))
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
            builder.append("  " + node.__repr__() + f" {self.nodes[node]}")
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


class ProvenanceStepPath(networkx.DiGraph):

    """
    ProvenanceStepPaths are subgraphs of ProvenanceStepGraphs that also contain an ordered list of nodes in a path.

    Implicitly this also defines an ordered set of edges in the path (of size len(path_nodes) - 1))
    """

    def __init__(self, path, graph: networkx.MultiDiGraph):
        super().__init__(self)
        self.path_nodes = path
        subgraph: networkx.MultiDiGraph = graph.subgraph(self.path_nodes)
        self.add_nodes_from(subgraph.nodes())
        for node_a, node_b, key in subgraph.edges(keys=True):
            self.add_edge(node_a, node_b, key=key)

    @property
    def path_edges(self):
        for node_a, node_b in zip(self.path_nodes[0:-1], self.path_nodes[1:]):
            edge = (
                (node_a, node_b)
                if (node_a, node_b) in self.edges()
                else (node_b, node_a)
            )
            yield (edge[0], edge[1], self.edges[edge[0], edge[1]])


class ArtifactFrameGraph(networkx.DiGraph):

    """
    A graph representation of spatial frames - aka how artifacts are spatially related to each other

    The graph consists of digital artifacts linked by spatial transforms - transforms map the coordinate
    systems of one artifact to another.  Each edge between artifacts is associated with a spatial frame.
    """

    ArtifactNode = ProvenanceStepGraph.ArtifactNode

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


class ArtifactFramePath(networkx.DiGraph):

    """
    ArtifactFramePaths are subgraphs of FrameGraphs that also contain an ordered list of nodes in a path.

    Implicitly this also defines an ordered set of edges in the path (of size len(path_nodes) - 1))
    """

    def __init__(self, path, graph: networkx.DiGraph):
        super().__init__(self)
        self.path_nodes = path
        subgraph = graph.subgraph(self.path_nodes)
        self.add_nodes_from(subgraph.nodes())
        self.add_edges_from(subgraph.edges(data=True))

    @property
    def path_edges(self):
        for node_a, node_b in zip(self.path_nodes[0:-1], self.path_nodes[1:]):
            edge = (
                (node_a, node_b)
                if (node_a, node_b) in self.edges()
                else (node_b, node_a)
            )
            yield (edge[0], edge[1], self.edges[edge[0], edge[1]])


class ProvenanceServices:

    """
    Services related to exploring the provenance of artifacts and operations
    """

    def __init__(self, service_layer):
        from .service_layer import ServiceLayer

        self.service_layer: ServiceLayer = service_layer
        self.repo_layer = self.service_layer.repo_layer

    def build_operation_steps(self, operation: models.Operation) -> ProvenanceStepGraph:
        """
        Build the operation steps and artifact relationships for a single operation
        """
        schema = (
            self.service_layer.schema_services()
            .query_resolved_project_schema(
                operation.project, type_urns=[operation.type_urn]
            )
            .schema_model
        )
        return ProvenanceStepGraph().build_from_operation(operation, schema)

    def build_artifact_provenance(
        self,
        artifact_id,
        strategy: str = None,
        include_motif_attrs=False,
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

        artifact_ids = (
            artifact_id if isinstance(artifact_id, (tuple, list)) else [artifact_id]
        )

        provenance_graph = ProvenanceStepGraph()
        fringe = [
            ProvenanceStepGraph.ArtifactNode(artifact_id=str(artifact_id))
            for artifact_id in artifact_ids
        ]
        seen_artifact_nodes: Set[ProvenanceStepGraph.ArtifactNode] = set(fringe)

        operations_repo: repositories.OperationRepository = self.repo_layer.operations
        artifacts_repo: repositories.ArtifactRepository = self.repo_layer.artifacts
        artifact_cb = lambda id: artifacts_repo.query_one(id=id)

        while fringe:
            next_artifact_node = fringe.pop()

            artifact_operations = operations_repo.query_by_attached(
                artifact_id=next_artifact_node.artifact_id, active=True
            )

            for operation in artifact_operations:
                schema_cb = (
                    lambda: self.service_layer.schema_services()
                    .query_resolved_project_schema(
                        operation.project, type_urns=[operation.type_urn]
                    )
                    .schema_model
                )

                extended_provenance = provenance_graph.extend_with_operation(
                    operation,
                    schema_cb,
                    next_artifact_node,
                    strategy=strategy,
                    include_motif_attrs=include_motif_attrs,
                    artifact_cb=artifact_cb,
                )

                for artifact_node in extended_provenance.nodes():
                    if not isinstance(artifact_node, ProvenanceStepGraph.ArtifactNode):
                        continue

                    if artifact_node not in seen_artifact_nodes:
                        fringe.append(artifact_node)
                        seen_artifact_nodes.add(artifact_node)

        return provenance_graph

    def query_artifact_provenance(
        self,
        from_artifact_id,
        cypher_query,
        **kwargs,
    ):
        """
        Query artifact(s) provenance via a cypher graph query.  Attributes for the query are pulled from the
        operation and artifact nodes.

        Currently only node return is supported.

        TODO: Include other query types
        """

        artifact_provenance_graph = self.build_artifact_provenance(
            from_artifact_id, include_motif_attrs=True, **kwargs
        )

        results = grandcypher.GrandCypher(
            networkx.DiGraph(artifact_provenance_graph)
        ).run(cypher_query)

        return (results, artifact_provenance_graph)

    def build_artifact_frame_graph(self, artifact_id, strategy: str = None):
        """
        Grow a frame graph starting from a particular artifact.

        The exact exploration strategy is configurable to "full", "parents", and "children".

        The exploration proceed/s by:
          - finding all frame parents and/or children of the current artifact node
            - parents are artifacts that are spatial_frame.parent_frames of the current artifact
            - children are artifacts that reference the current artifact in their spatial_frame.parent_frame
          - adding the parent and/or children edges (and nodes, implicitly) to the growing graph
          - finding unexplored parent/children from above to explore next
          - continue until all seen artifacts are explored
        """

        artifact_ids = (
            artifact_id if isinstance(artifact_id, (tuple, list)) else [artifact_id]
        )

        if strategy is None:
            strategy = "full"

        frame_graph = ArtifactFrameGraph()
        fringe = [
            ArtifactFrameGraph.ArtifactNode(artifact_id=str(artifact_id))
            for artifact_id in artifact_ids
        ]

        artifacts_repo: repositories.ArtifactRepository = self.repo_layer.artifacts

        while fringe:
            next_artifact_node = fringe.pop()

            frame_graph.add_node(next_artifact_node)
            
            if strategy == "full" or strategy == "parents":
                
                next_artifact: models.AnyArtifact = artifacts_repo.query_one(next_artifact_node.artifact_id)
                
                if next_artifact.spatial_frame is not None and next_artifact.spatial_frame.parent_frame is not None:
                    
                    parent_node = ArtifactFrameGraph.ArtifactNode(artifact_id=str(next_artifact.spatial_frame.parent_frame))
                    
                    if parent_node not in frame_graph:
                        fringe.append(parent_node)

                    frame_graph.add_edge(parent_node, next_artifact_node, frame=next_artifact.spatial_frame)

            if strategy == "full" or strategy == "children":
                
                for child_artifact in list(artifacts_repo.query(parent_frame_id=next_artifact_node.artifact_id)):
                    
                    child_artifact_node = ArtifactFrameGraph.ArtifactNode(artifact_id=str(child_artifact.id))

                    if child_artifact_node not in frame_graph:
                        fringe.append(child_artifact_node)

                    frame_graph.add_edge(next_artifact_node, child_artifact_node, frame=child_artifact.spatial_frame)

        return frame_graph

    def build_artifact_frame_path(self, from_artifact_id, to_artifact_id):
        """
        Grow a frame graph path starting from a particular artifact and ending at another artifact.

        The path, which includes the transforms along the edges of the path, encodes the full set of
        information needed to transform one digital artifact coordinate system into another.
        """

        frame_graph = self.build_artifact_frame_graph(from_artifact_id, strategy="full")
        undir_frame_graph = frame_graph.to_undirected(as_view=True)

        from_artifact_node = ArtifactFrameGraph.ArtifactNode(
            artifact_id=str(from_artifact_id)
        )
        to_artifact_node = ArtifactFrameGraph.ArtifactNode(
            artifact_id=str(to_artifact_id)
        )

        for node in (from_artifact_node, to_artifact_node):
            if node not in frame_graph.nodes():
                return None

        try:
            return ArtifactFramePath(
                networkx.algorithms.shortest_path(
                    undir_frame_graph, from_artifact_node, to_artifact_node
                ),
                frame_graph,
            )
        except networkx.NetworkXNoPath:
            return None

    def build_nearest_related_artifact_frame_path(
        self,
        from_artifact_id,
        related_artifact_cypher_query,
        to_artifact_id,
        **kwargs,
    ):
        """
        Build a frame path from the from_artifact to the nearest digital artifact related to the to_artifact.

        Returns the ProvenanceStepPath between the from_artifact and the nearest related digital artifact, as
        well as the shortest FramePath between the nearest related artifact and the to_artifact.

        A related_artifact_cypher_query is used to filter the nearest related digital artifacts if particular
        types of artifacts are wanted.
        """

        related_artifact_results, provenance_graph = self.query_artifact_provenance(
            from_artifact_id, related_artifact_cypher_query, **kwargs
        )

        if not related_artifact_results:
            return None

        related_artifact_nodes = next(related_artifact_results.items().__iter__())[1]

        frame_graph = self.build_artifact_frame_graph(to_artifact_id, strategy="full")

        frame_related_artifact_nodes = set(frame_graph.nodes).intersection(
            related_artifact_nodes
        )

        if not frame_related_artifact_nodes:
            return None

        undir_provenance_graph = provenance_graph.to_undirected(as_view=True)

        from_artifact_node = ProvenanceStepGraph.ArtifactNode(
            artifact_id=str(from_artifact_id)
        )

        to_artifact_node = ProvenanceStepGraph.ArtifactNode(
            artifact_id=str(to_artifact_id)
        )

        provenance_paths = [
            networkx.algorithms.shortest_path(
                undir_provenance_graph, from_artifact_node, frame_related_artifact_node
            )
            for frame_related_artifact_node in frame_related_artifact_nodes
        ]

        shortest_provenance_path = ProvenanceStepPath(
            sorted(provenance_paths, key=lambda p: len(p))[0], provenance_graph
        )

        undir_frame_graph = frame_graph.to_undirected(as_view=True)

        shortest_frame_path = ArtifactFramePath(
            networkx.algorithms.shortest_path(
                undir_frame_graph,
                shortest_provenance_path.path_nodes[-1],
                to_artifact_node,
            ),
            frame_graph,
        )

        return (shortest_provenance_path, shortest_frame_path)
