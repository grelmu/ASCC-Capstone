import json
import typing
import networkx
import functools

from .. import models
from .. import schemas


class ResolvedSchema(models.StoredSchema):
    schema_model: typing.Any


class SchemaServices:

    """
    Services related to schemas for data in the warehouse
    """

    def __init__(self, service_layer):

        from .service_layer import ServiceLayer

        self.service_layer: ServiceLayer = service_layer
        self.repo_layer = self.service_layer.repo_layer

    def query_project_schemas(
        self,
        project_id,
        module_names=None,
        type_urns=None,
        type_urn_prefix=None,
        active=True,
        current=True,
    ):

        project: models.Project = self.repo_layer.projects.query_one(ids=[project_id])

        user_schemas = self.repo_layer.user_schemas.query(
            project_ids=[project_id],
            type_urns=type_urns,
            type_urn_prefix=type_urn_prefix,
            active=active,
        )

        # Filter module names that aren't relevant to the project
        if project.included_schema_modules is None:
            project.included_schema_modules = schemas.get_schema_module_names()
        if module_names is None:
            module_names = project.included_schema_modules

        module_names = list(
            set(project.included_schema_modules).intersection(module_names)
        )

        module_schemas = self.repo_layer.module_schemas.query(
            module_names=module_names,
            type_urns=type_urns,
            type_urn_prefix=type_urn_prefix,
            active=active,
        )

        project_schemas = list(user_schemas) + list(module_schemas)

        if not current:
            return project_schemas

        # Figure out the latest active schemas of each type
        project_schemas = sorted(
            project_schemas,
            key=lambda schema: (
                1 if schema.active else 0,
                1 if schema.module is None else 0,
                schema.type_urn,
                str(schema.id),
            ),
            reverse=True,
        )

        current_schemas = {}
        for schema in project_schemas:
            if schema.type_urn not in current_schemas:
                current_schemas[schema.type_urn] = schema

        return list(current_schemas.values())

    def resolve_project_schemas(
        self,
        project_id,
        unresolved_schemas: typing.List[models.StoredSchema],
    ):
        schema_family: networkx.DiGraph = self._find_project_schema_family(
            project_id, unresolved_schemas
        )

        unresolved_schema_urns = set(map(lambda s: s.type_urn, unresolved_schemas))

        for type_urn in networkx.topological_sort(schema_family):

            schema_model = schema_family.nodes[type_urn]["schema_model"]
            for parent_type_urn in schema_model.parent_urns or []:

                parent_schema_model = schema_family.nodes[parent_type_urn][
                    "schema_model"
                ]

                schema_model.attachments.child_kinds.extend(
                    parent_schema_model.attachments.child_kinds
                )
                # TODO: Extend types

            if type_urn in unresolved_schema_urns:
                stored_schema = schema_family.nodes[type_urn]["stored_schema"]
                yield ResolvedSchema(
                    schema_model=schema_model, **(stored_schema.dict())
                )

    def query_resolved_project_schemas(self, project_id, *args, **kwargs):
        project_schemas = self.query_project_schemas(project_id, *args, **kwargs)
        return self.resolve_project_schemas(project_id, project_schemas)

    def _find_project_schema_family(
        self, project_id, stored_schemas: typing.List[models.StoredSchema]
    ):

        schema_family = networkx.DiGraph()
        fringe = []

        for next_stored_schema in stored_schemas:
            if next_stored_schema.type_urn not in schema_family.nodes():
                next_schema_model = self._load_schema_model(
                    next_stored_schema.storage_schema_json
                )
                schema_family.add_node(
                    next_stored_schema.type_urn,
                    stored_schema=next_stored_schema,
                    schema_model=next_schema_model,
                )
                fringe.append(next_stored_schema.type_urn)

        while fringe:

            next_schema_type_urn = fringe.pop()
            next_schema_model = schema_family.nodes[next_schema_type_urn][
                "schema_model"
            ]

            parent_type_urns = next_schema_model.parent_urns or []
            unseen_parent_type_urns = list(
                set(parent_type_urns).difference(schema_family.nodes())
            )

            if unseen_parent_type_urns:
                for parent_stored_schema in self.query_project_schemas(
                    project_id,
                    type_urns=unseen_parent_type_urns,
                    current=True,
                ):
                    parent_schema_model = self._load_schema_model(
                        parent_stored_schema.storage_schema_json
                    )
                    schema_family.add_node(
                        parent_stored_schema.type_urn,
                        stored_schema=parent_stored_schema,
                        schema_model=parent_schema_model,
                    )
                    fringe.append(parent_stored_schema.type_urn)

            for parent_type_urn in parent_type_urns:
                schema_family.add_edge(parent_type_urn, next_schema_type_urn)

        return schema_family

    @functools.lru_cache(maxsize=1024)
    def _load_schema_model(
        self,
        schema_json,
    ):
        schema_obj = json.loads(schema_json)
        if schema_obj["type_urn"].startswith(models.Artifact.URN_PREFIX):
            return schemas.ArtifactSchema(**schema_obj)
        elif schema_obj["type_urn"].startswith(models.Operation.URN_PREFIX):
            return schemas.OperationSchema(**schema_obj)
        return None
