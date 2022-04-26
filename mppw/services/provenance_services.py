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


class ProvenanceStepGraph(networkx.MultiDiGraph):
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

        def __repr__(self):
            return f"{type(self).__name__}{self.__members()}"

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

        def __repr__(self):
            return f"{type(self).__name__}{self.__members()}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def build_from_operation(self, operation: models.Operation):

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

    def __human_str__(self):
        builder = []
        builder.append("Nodes:")
        for node in self.nodes():
            builder.append("  " + node.__repr__())
        builder.append("Edges:")
        for edge in self.edges(keys=True):
            builder.append("  " + edge.__repr__())
        return "\n".join(builder)


class ProvenanceServices:
    def __init__(self, service_layer):

        from .service_layer import ServiceLayer

        self.service_layer: ServiceLayer = service_layer
        self.repo_layer = self.service_layer.repo_layer

    def build_operation_steps(self, operation) -> ProvenanceStepGraph:
        return ProvenanceStepGraph().build_from_operation(operation)

    def build_artifact_provenance(
        self, artifact_id, strategy: str = None
    ) -> ProvenanceStepGraph:

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

    # def build_provenance(self, artifact_id: str):

    #     provenance_graph = ProvenanceGraph()
    #     fringe: List[ProvenanceGraph.ArtifactNode] = [
    #         provenance_graph.add_artifact_node(artifact_id)
    #     ]
    #     seen_artifact_nodes: Set[ProvenanceGraph.ArtifactNode] = set(fringe)

    #     operations_repo: repositories.OperationRepository = self.repo_layer.operations

    #     while fringe:

    #         next_artifact_node = fringe.pop()

    #         artifact_operations = operations_repo.query_by_attached(
    #             artifact_id=next_artifact_node.artifact_id
    #         )

    #         for operation in artifact_operations:

    #             relation_edges = provenance_graph.add_attachment_relations(
    #                 operation, next_artifact_node
    #             )

    #             for artifact_node_from, artifact_node_to, op_relation in relation_edges:
    #                 if artifact_node_from not in seen_artifact_nodes:
    #                     fringe.append(artifact_node_from)
    #                     seen_artifact_nodes.add(artifact_node_from)
    #                 if artifact_node_to not in seen_artifact_nodes:
    #                     fringe.append(artifact_node_to)
    #                     seen_artifact_nodes.add(artifact_node_to)

    #     return provenance_graph


# class ProvenanceRelation(enum.Enum):
#     MATERIAL_TRANSFORM = "material_transform"
#     MEASUREMENT = "measurement"


# class AttachmentRelationsGraph(models.AttachmentGraph):
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#     def build_from_operation(self, operation: models.Operation, type_urn_provider):
#         def filter_by_type(
#             nodes: Sequence[models.AttachmentGraph.AttachmentNode],
#             type_urn_provider,
#             type_re,
#         ):
#             if type_re is None:
#                 for node in nodes:
#                     yield node

#             for node, type_urn in zip(nodes, type_urn_provider(list(nodes))):
#                 if re.match(type_re, type_urn):
#                     yield node

#         provenance_schema = schemas.get_operation_schema(operation.type_urn).provenance

#         for relation_schema in provenance_schema.relations:

#             relation = ProvenanceRelation(relation_schema.name)

#             nodes_from = list(
#                 operation.attachments.find_nodes_by_path_re(
#                     relation_schema.from_kind_path_re
#                 )
#             )

#             for node_from in filter_by_type(
#                 nodes_from, type_urn_provider, relation_schema.from_type_urn_re
#             ):

#                 nodes_to = list(
#                     operation.attachments.find_nodes_by_path_re(
#                         relation_schema.to_kind_path_re, context=node_from
#                     )
#                 )

#                 for node_to in filter_by_type(
#                     nodes_to, type_urn_provider, relation_schema.to_type_urn_re
#                 ):
#                     self.add_edge(node_from, node_to, relation)

#         return self


# class ProvenanceGraph(networkx.MultiDiGraph):
#     class ArtifactNode:
#         def __init__(self, artifact_id):
#             self.artifact_id = str(artifact_id)

#         def __members(self):
#             return (self.artifact_id,)

#         def __eq__(self, other):
#             if type(other) is type(self):
#                 return self.__members() == other.__members()
#             else:
#                 return False

#         def __hash__(self):
#             return hash(self.__members())

#         def __repr__(self):
#             return f"{type(self).__name__}{self.__members()}"

#     class AttachmentRelation:
#         def __init__(
#             self, operation_id, attachment_node_from, attachment_node_to, relation
#         ):
#             self.operation_id = str(operation_id)
#             self.attachment_node_from = attachment_node_from
#             self.attachment_node_to = attachment_node_to
#             self.relation = relation

#         def __members(self):
#             return (
#                 self.operation_id,
#                 self.attachment_node_from,
#                 self.attachment_node_to,
#                 self.relation,
#             )

#         def __eq__(self, other):
#             if type(other) is type(self):
#                 return self.__members() == other.__members()
#             else:
#                 return False

#         def __hash__(self):
#             return hash(self.__members())

#         def __repr__(self):
#             return f"{type(self).__name__}{self.__members()}"

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#     def __human_str__(self):
#         builder = []
#         builder.append("Nodes:")
#         for node in self.nodes():
#             builder.append("  " + node.__repr__())
#         builder.append("Edges:")
#         for edge in self.edges(keys=True):
#             builder.append("  " + edge.__repr__())
#         return "\n".join(builder)

#     def add_artifact_node(self, artifact_id):
#         node = ProvenanceGraph.ArtifactNode(artifact_id)
#         self.add_node(node)
#         return node

#     def get_artifact_node(self, artifact_id):
#         node = ProvenanceGraph.ArtifactNode(artifact_id)
#         if node in self.nodes:
#             return node
#         return None

#     def has_artifact_nodes(self, artifact_id):
#         return self.get_artifact_node(artifact_id) is not None

#     def add_attachment_relations(
#         self,
#         operation: models.Operation,
#         artifact_node: ArtifactNode,
#         cached_relations: dict = {},
#     ):

#         attachment_relations: AttachmentRelationsGraph = cached_relations.get(
#             operation.id
#         )
#         if attachment_relations is None:
#             attachment_relations = AttachmentRelationsGraph().build_from_operation(
#                 operation
#             )

#         relation_edges = []

#         for attachment_node in attachment_relations.find_nodes_by_artifact(
#             artifact_node.artifact_id
#         ):

#             for attachment_node_from, _, relation in attachment_relations.in_edges(
#                 attachment_node, keys=True
#             ):

#                 artifact_node_from = ProvenanceGraph.ArtifactNode(
#                     attachment_node_from.artifact_id
#                 )
#                 self.add_node(artifact_node_from)

#                 relation = ProvenanceGraph.AttachmentRelation(
#                     operation.id, attachment_node_from, attachment_node, relation
#                 )
#                 relation_edge = (artifact_node_from, artifact_node, relation)

#                 self.add_edge(*relation_edge)
#                 relation_edges.append(relation_edge)

#             for _, attachment_node_to, relation in attachment_relations.out_edges(
#                 attachment_node, keys=True
#             ):

#                 artifact_node_to = ProvenanceGraph.ArtifactNode(
#                     attachment_node_to.artifact_id
#                 )
#                 self.add_node(artifact_node_to)

#                 relation = ProvenanceGraph.AttachmentRelation(
#                     operation.id, attachment_node, attachment_node_to, relation
#                 )
#                 relation_edge = (artifact_node, artifact_node_to, relation)

#                 self.add_edge(*relation_edge)
#                 relation_edges.append(relation_edge)

#         return relation_edges
