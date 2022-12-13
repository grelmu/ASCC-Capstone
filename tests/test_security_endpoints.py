import pytest
import requests.exceptions

from mppw_clients import mppw_clients

import mppw.security


def test_create_users_basic(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Tests that we can create users via the API
    """

    api = api_pytest_client

    user = api.create_user(
        {
            "username": "basic_user",
            "allowed_scopes": [
                mppw.security.READ_PROVENANCE_SCOPE,
                mppw.security.MODIFY_PROVENANCE_SCOPE,
            ],
            "local_claims": api.default_claims,
            "password": "password",
        }
    )

    api.login("basic_user", "password")

    assert "basic_user" == api.get_me_user()["username"]

    try:
        api.find_users()
        # Should not succeed
        assert False
    except requests.exceptions.HTTPError as ex:
        assert ex.response.status_code == 401


def test_provenance_permissions_basic(api_pytest_client: mppw_clients.MppwApiClient):

    """
    Tests that provenance permissions work as expected
    """

    api = api_pytest_client

    #
    # Read/Write user
    #

    user = api.create_user(
        {
            "username": "rw_user",
            "allowed_scopes": [
                mppw.security.MODIFY_PROVENANCE_SCOPE,
            ],
            "local_claims": api.default_claims,
            "password": "password",
        }
    )

    admin_headers = api.headers
    api.login("rw_user", "password")

    successes = [
        lambda: api.find_projects(),
        lambda: api.find_artifacts(),
        lambda: api.find_operations(),
        lambda: api.create_artifact(
            {
                "name": "Security Artifact",
                "type_urn": "urn:x-mfg:artifact:digital:document",
            }
        ),
        lambda: api.create_artifact(
            {
                "name": "Editable Security Artifact",
                "type_urn": "urn:x-mfg:artifact:digital:document",
            }
        ),
        lambda: api.create_artifact(
            {
                "name": "Temp Security Artifact",
                "type_urn": "urn:x-mfg:artifact:digital:document",
            }
        ),
        lambda: api.delete_artifact(
            api.find_artifact(name="Temp Security Artifact")["id"]
        ),
        lambda: api.create_operation(
            {
                "name": "Security Operation",
                "type_urn": "urn:x-mfg:operation:default",
            },
            init=True,
        ),
        lambda: api.create_operation(
            {
                "name": "Temp Security Operation",
                "type_urn": "urn:x-mfg:operation:default",
            },
            init=True,
        ),
        lambda: api.delete_operation(
            api.find_operation(name="Temp Security Operation")["id"]
        ),
    ]

    failures = [
        lambda: api.create_project({"name": "Invalid Project"}),
    ]

    for success in successes:
        success()

    for failure in failures:
        try:
            failure()
            # Should not succeed
            assert False
        except requests.exceptions.HTTPError as ex:
            assert ex.response.status_code == 401

    #
    # Read-only user
    #

    api.headers = admin_headers
    user = api.create_user(
        {
            "username": "ro_user",
            "allowed_scopes": [
                mppw.security.READ_PROVENANCE_SCOPE,
            ],
            "local_claims": api.default_claims,
            "password": "password",
        }
    )

    api.login("ro_user", "password")

    successes = [
        lambda: api.find_projects(),
        lambda: api.find_artifacts(),
        lambda: api.find_operations(),
        lambda: api.get_artifact(api.find_artifact(name="Security Artifact")["id"]),
        lambda: api.get_operation(api.find_operation(name="Security Operation")["id"]),
    ]

    failures = [
        lambda: api.create_project({"name": "Invalid Project"}),
        lambda: api.create_artifact(
            {
                "name": "Security Artifact",
                "type_urn": "urn:x-mfg:artifact:digital:document",
            }
        ),
        lambda: api.delete_artifact(api.find_artifact(name="Security Artifact")["id"]),
        lambda: api.create_operation(
            {
                "name": "Security Operation",
                "type_urn": "urn:x-mfg:operation:default",
            },
            init=True,
        ),
        lambda: api.delete_operation(
            api.find_operation(name="Security Operation")["id"]
        ),
    ]

    for success in successes:
        success()

    for failure in failures:
        try:
            failure()
            # Should not succeed
            assert False
        except requests.exceptions.HTTPError as ex:
            assert ex.response.status_code == 401

    #
    # Artifact-only user
    #

    api.headers = admin_headers
    user = api.create_user(
        {
            "username": "artifact_user",
            "allowed_scopes": [
                mppw.security.READ_PROVENANCE_SCOPE,
                mppw.security.MODIFY_ARTIFACT_SCOPE,
            ],
            "local_claims": api.default_claims,
            "password": "password",
        }
    )

    api.login("artifact_user", "password")

    successes = [
        lambda: api.update_artifact(
            api.find_artifact(name="Editable Security Artifact")
        ),
    ]

    failures = [
        lambda: api.create_artifact(
            {
                "name": "Security Artifact",
                "type_urn": "urn:x-mfg:artifact:digital:document",
            }
        ),
        lambda: api.delete_artifact(api.find_artifact(name="Security Artifact")["id"]),
    ]

    for success in successes:
        success()

    for failure in failures:
        try:
            failure()
            # Should not succeed
            assert False
        except requests.exceptions.HTTPError as ex:
            assert ex.response.status_code == 401
