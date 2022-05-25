import pytest
import json

from mppw import services

"""
Unit tests of the services layer
"""

def test_services_load_qualname():

    """
    Tests that a service class can be found from a qualified name
    """

    qualname = "mppw.services.artifacts.digital_file_services:FileServices"

    service_class = services.ServiceLayer.load_service_class(qualname)

    from mppw.services.artifacts.digital_file_services import FileServices

    assert service_class == FileServices
