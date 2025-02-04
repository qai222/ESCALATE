import pytest
from django.test import RequestFactory as rf
from django.test import Client
from django.urls import reverse
from typing import Any

from core.utilities.utils import view_names, camel_to_snake
from core.views.crud_view_methods.create_methods import methods as create_methods
from core.views.crud_view_methods.delete_methods import methods as delete_methods
from core.views.crud_view_methods.detail_methods import methods as detail_methods
from core.views.crud_view_methods.list_methods import methods as list_methods
from core.views.crud_view_methods.update_methods import methods as update_methods
from core.views.exports.export_methods import methods as export_methods
from core.views.exports.file_types import file_types as export_file_types

pytestmark = pytest.mark.django_db

from bs4 import BeautifulSoup
import re

"""
data needs to be added to db before these tests will run properly. can add data for each test or we can preload data like gary did with sql
"""

# TODO need to add data to db before test is run
client = Client()

(
    create_names,
    delete_names,
    detail_names,
    list_names,
    export_names,
    update_methods,
    *_,
) = [[] for i in range(6)]

for model_name in view_names:
    if model_name in create_methods:
        create_names.append(f"{camel_to_snake(model_name)}_add")
    if model_name in delete_methods:
        delete_names.append(f"{camel_to_snake(model_name)}_delete")
    if model_name in detail_methods:
        detail_names.append(f"{camel_to_snake(model_name)}_view")
    if model_name in list_methods:
        list_names.append(f"{camel_to_snake(model_name)}_list")
    if model_name in export_methods:
        for file_type in export_file_types:
            export_names.append(f"{camel_to_snake(model_name)}_export_{file_type}")


def get_organization(
    organization,
    login=False,
):
    """
    Gets the value of Testco based on the dropdown menu in a specific page
    """
    if not login:
        select_id = "org_select"
        page = "select_lab"
    else:
        select_id = "id_organization"
        page = "user_profile"
    response = client.get(reverse(page))
    soup = BeautifulSoup(response.content, "html.parser")
    return soup.find(id=select_id).find_all("option", text=re.compile(organization))[0][
        "value"
    ]


def set_client_org_to_org(organization):
    uuid = get_organization(organization)
    client.post(reverse("select_lab"), {"select_org": "select_org", "org_select": uuid})


@pytest.fixture
def login():
    """
    Logs user in and adds the organization to the user
    """
    client.post("", {"username": "vshekar", "password": "copperhead123"})
    client.post(
        reverse("user_profile"),
        {
            "add_org": "add_org",
            "organization": get_organization("TestCo", login=True),
            "password": "test",
        },
    )


def test_create_user():
    """
    Opens create_user page
    """
    response = client.get(reverse("create_user"))
    assert response.status_code == 200


@pytest.mark.ui_basic_tests
def test_workflow(login):
    """
    Opens user_profile page
    """
    set_client_org_to_org("TestCo")
    response = client.get(reverse("workflow"))
    assert response.status_code == 200


@pytest.mark.ui_basic_tests
def test_create_experiment(login):
    """
    Creates experiment
    """
    set_client_org_to_org("Haverford College")
    response = client.get(reverse("experiment_instance_add"))
    assert response.status_code == 200


def test_create_exp_template():
    et_data: list[dict[str, Any]] = [
        {
            "template_name": "test_template",
            "select_rt": [
                "69ba96cc-d30e-41ca-a543-83a8b5b92b9c",
                "d9a6a7aa-b5ac-4039-af8a-353b6b1b1aae",
                "390e814f-6339-46f1-9e96-f01720ea90fa",
                "074b4b61-7a4b-4d71-8910-2033110e53ce",
            ],
            "column_order": "ACBDEGFH",
            "rows": 12,
            "select_vessel": ["6f8051a7-19f3-4000-aa21-a3e5ac193f28"],
            "select_actions": [
                "476ceea0-6154-4da3-b073-dd5ad68ea4d6",
                "849fb9fa-2f8d-4e97-85e3-9cdbd5c70e0b",
                "7f716a7a-cace-4ee8-9eae-0ebc18550454",
            ],
            "define_outcomes": "Crystal score",
        },
        {},
    ]
    response = client.post(reverse("experiment_template_add"), et_data[0], follow=True)
    assert response.status_code == 200


@pytest.mark.ui_basic_tests
def test_user_profile(login):
    """
    Opens user_profile page
    """
    set_client_org_to_org("TestCo")
    response = client.get(reverse("user_profile"))
    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")

    # test editting user profile
    edit_elements = soup.select(".edit-account-profile")
    if len(edit_elements) > 0:
        edit_link = edit_elements[0]["href"]
        response = client.get(edit_link)
        assert (
            response.status_code == 200
        ), f"clicking edit profile from user profile FAILED"
    else:
        assert True
    # test clicking change password
    password_elements = soup.select(".edit-account-password")
    if len(password_elements) > 0:
        password_link = password_elements[0]["href"]
        response = client.get(password_link)
        assert (
            response.status_code == 200
        ), f"clicking change password from user profile FAILED"
    else:
        assert True


@pytest.mark.ui_basic_tests
@pytest.mark.parametrize("name", list_names)
def test_generic_list_views(login, name):
    """
    Opens detail page for each model's list view in list_names
    """
    set_client_org_to_org("TestCo")

    response = client.get(reverse(name))
    # test list view rendering
    assert response.status_code == 200, f"{name} did not render"

    # TODO test clicking sorting buttons in each column
    soup = BeautifulSoup(response.content, "html.parser")

    # test clicking detail link from list view
    view_detail_elements = soup.select(".view-detail")
    if len(view_detail_elements) > 0:
        view_link = view_detail_elements[0]["href"]
        response = client.get(view_link)
        assert response.status_code == 200, f"clicking detail from {name} FAILED"
    else:
        assert True
    # test clicking update link from list view
    view_update_elements = soup.select(".view-update")
    if len(view_update_elements) > 0:
        view_link = view_update_elements[0]["href"]
        response = client.get(view_link)
        assert response.status_code == 200, f"clicking update from {name} FAILED"
    else:
        assert True
    # test clicking create link from list view
    view_link = soup.select(".view-add")[0]["href"]
    response = client.get(view_link)
    assert response.status_code == 200, f"clicking create from {name} FAILED"
    # TODO test clicking delete from list view

    # TODO test clicking export buttons


@pytest.mark.ui_basic_tests
@pytest.mark.parametrize("name", export_names)
def test_generic_export_views(login, name):
    """
    Opens detail page for each model's list view in list_names
    """
    set_client_org_to_org("TestCo")

    response = client.get(reverse(name))
    assert response.status_code == 200, f"{name} FAILED"
