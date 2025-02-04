from rest_api.tests.post_put_delete_tests import add_prev_endpoint_data_2
from ..model_tests_utils import (
    status_codes,
    DELETE,
    PUT,
    POST,
    GET,
    ERROR,
    random_model_dict,
    check_status_code,
)
from core.models import Organization, Systemtool, Person, SystemtoolType


def check_actor(resp, **kwargs):
    # Ex:
    # actor_fields = {
    #     'organization': 'some_org__url',
    #     'person': 'some_person__url',
    #     ...
    # }
    actor_fields = kwargs["actor_fields"]

    response_data = kwargs["response_data"]

    urls = add_prev_endpoint_data_2(actor_fields, response_data)

    # find all the actors with organization=x, person=y, systemtool=z
    filter_method = lambda actor: all(
        actor[actor_field] == url for actor_field, url in urls.items()
    )
    return len(list(filter(filter_method, resp.json()["results"]))) == 1


actor_tests = [
    [
        {
            "name": "org0",
            "method": POST,
            "endpoint": "organization-list",
            "body": random_model_dict(Organization),
            "args": [],
            "query_params": [],
            "is_valid_response": {
                "function": check_status_code,
                "args": [],
                "kwargs": {"status_code": POST},
            },
        },
        {
            "name": "org0_get_actor",
            "method": GET,
            "endpoint": "actor-list",
            "body": {},
            "args": [],
            "query_params": [],
            "is_valid_response": {
                "function": check_actor,
                "args": [],
                "kwargs": {
                    "actor_fields": {"organization": "org0__url"},
                },
            },
        },
        {
            "name": "person0",
            "method": POST,
            "endpoint": "person-list",
            "body": random_model_dict(Person),
            "args": [],
            "query_params": [],
            "is_valid_response": {
                "function": check_status_code,
                "args": [],
                "kwargs": {"status_code": POST},
            },
        },
        {
            "name": "person0_get_actor",
            "method": GET,
            "endpoint": "actor-list",
            "body": {},
            "args": [],
            "query_params": [],
            "is_valid_response": {
                "function": check_actor,
                "args": [],
                "kwargs": {
                    "actor_fields": {"person": "person0__url"},
                },
            },
        },
        {
            "name": "systemtooltype0",
            "method": POST,
            "endpoint": "systemtooltype-list",
            "body": random_model_dict(SystemtoolType),
            "args": [],
            "query_params": [],
            "is_valid_response": {
                "function": check_status_code,
                "args": [],
                "kwargs": {"status_code": POST},
            },
        },
        {
            "name": "systemtool0",
            "method": POST,
            "endpoint": "systemtool-list",
            "body": random_model_dict(
                Systemtool,
                vendor_organization="org0__url",
                systemtool_type="systemtooltype0__url",
            ),
            "args": [],
            "query_params": [],
            "is_valid_response": {
                "function": check_status_code,
                "args": [],
                "kwargs": {"status_code": POST},
            },
        },
        {
            "name": "systemtool0_get_actor",
            "method": GET,
            "endpoint": "actor-list",
            "body": {},
            "args": [],
            "query_params": [],
            "is_valid_response": {
                "function": check_actor,
                "args": [],
                "kwargs": {
                    "actor_fields": {"systemtool": "systemtool0__url"},
                },
            },
        },
    ]
]
