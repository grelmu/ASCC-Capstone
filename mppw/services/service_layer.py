import importlib
from typing import Optional, List, ClassVar, Any, Union

from mppw import logger

from .. import models
from .. import schemas

from .artifact_services import ArtifactServices
from .operation_services import OperationServices
from .provenance_services import ProvenanceServices
from .schema_services import SchemaServices


class ServiceLayer:

    """
    A ServiceLayer provides access to abstracted types of services on top of durable data storage.

    Generally all (nontrivial) logical data warehouse actions should be accessible here.
    """

    def __init__(self, repo_layer):
        self.repo_layer = repo_layer

    @staticmethod
    def load_service_class(qualname: str):
        module_name, class_name = qualname.split(":")
        module = importlib.import_module(module_name)
        return getattr(module, class_name)

    def artifact_services_for(
        self, type_urn: Union[str, models.Artifact], service_type=None
    ) -> ArtifactServices:

        """
        Given an artifact, returns the specialized services for that type of artifact
        """

        if isinstance(type_urn, models.Artifact):
            type_urn = type_urn.type_urn

        schema = schemas.get_artifact_schema(type_urn, default_schema_if_missing=True)

        service_class_qualname = schema.services.class_qualname
        if service_class_qualname is None:
            service_class_qualname = "mppw.services.artifact_services:ArtifactServices"

        service_class = ServiceLayer.load_service_class(service_class_qualname)

        if service_class is None:
            raise Exception(
                f"Cannot find service class {service_class_qualname} for artifact of type {type_urn}"
            )

        services = service_class(self, schema)

        if service_type is not None and not isinstance(services, service_type):
            raise Exception(
                f"Artifact of type {type_urn} is not compatible with service type {service_type}"
            )

        return services

    def artifact_service(self, type_urn) -> ArtifactServices:
        return self.artifact_services_for(type_urn)

    def operation_services_for(
        self, type_urn: Union[str, models.Operation], service_type=None
    ) -> OperationServices:

        """
        Given an operation, returns the specialized services for that type of operation
        """

        if isinstance(type_urn, models.Operation):
            type_urn = type_urn.type_urn

        schema = schemas.get_operation_schema(type_urn, default_schema_if_missing=True)

        service_class_qualname = schema.services.class_qualname
        if service_class_qualname is None:
            service_class_qualname = (
                "mppw.services.operation_services:OperationServices"
            )

        service_class = ServiceLayer.load_service_class(service_class_qualname)

        if service_class is None:
            raise Exception(
                f"Cannot find service class {service_class_qualname} for operation of type {type_urn}"
            )

        services = service_class(self, schema)

        if service_type is not None and not isinstance(services, service_type):
            raise Exception(
                f"Operation of type {type_urn} is not compatible with service type {service_type}"
            )

        return services

    def operation_service(self, type_urn) -> OperationServices:
        return self.operation_services_for(type_urn)

    def provenance_services(self):
        return ProvenanceServices(self)

    def schema_services(self):
        return SchemaServices(self)
