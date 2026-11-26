"""GET /api/contacts and /api/contacts/{id}. Expected results are computed from the seed file."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from crm_api.seed import read_seed
from crm_api.text import collation_key

SEED = read_seed()
COMPANY_NAMES = {company["id"]: company["name"] for company in SEED["companies"]}
SELLER_ID = "usr_2"
SELLER_CONTACTS = [c for c in SEED["contacts"] if c["ownerId"] == SELLER_ID]
OTHERS_CONTACT = next(c for c in SEED["contacts"] if c["ownerId"] != SELLER_ID)


def get(client: TestClient, headers: dict[str, str], **params: Any) -> dict[str, Any]:
    response = client.get("/api/contacts", params=params, headers=headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def all_pages(client: TestClient, headers: dict[str, str], **params: Any) -> list[dict[str, Any]]:
    first: list[dict[str, Any]] = get(client, headers, pageSize=100, **params)["data"]
    second: list[dict[str, Any]] = get(client, headers, pageSize=100, page=2, **params)["data"]
    return first + second


def test_admin_sees_every_contact(client: TestClient, admin_headers: dict[str, str]) -> None:
    body = get(client, admin_headers)

    assert body["total"] == 180
    assert body["page"] == 1
    assert body["pageSize"] == 20
    assert len(body["data"]) == 20


def test_seller_sees_only_their_own_contacts(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    contacts = all_pages(client, seller_headers)

    assert len(contacts) == len(SELLER_CONTACTS) > 0
    assert {contact["ownerId"] for contact in contacts} == {SELLER_ID}


def test_contact_has_the_contract_shape(client: TestClient, admin_headers: dict[str, str]) -> None:
    contact = get(client, admin_headers, pageSize=1)["data"][0]

    assert set(contact) == {
        "id",
        "name",
        "email",
        "phone",
        "jobTitle",
        "companyId",
        "ownerId",
        "createdAt",
        "company",
    }
    assert contact["company"] == {
        "id": contact["companyId"],
        "name": COMPANY_NAMES[contact["companyId"]],
    }
    assert contact["createdAt"].endswith("Z")


def sort_key(sort: str) -> Any:
    keys = {
        "name": lambda c: collation_key(c["name"]),
        "email": lambda c: collation_key(c["email"]),
        "company": lambda c: collation_key(COMPANY_NAMES[c["companyId"]]),
        "createdAt": lambda c: c["createdAt"],
    }
    return keys[sort]


@pytest.mark.parametrize("sort", ["name", "email", "company", "createdAt"])
@pytest.mark.parametrize("order", ["asc", "desc"])
def test_contacts_are_sorted(
    client: TestClient, admin_headers: dict[str, str], sort: str, order: str
) -> None:
    contacts = all_pages(client, admin_headers, sort=sort, order=order)

    keys = [sort_key(sort)(contact) for contact in contacts]
    assert keys == sorted(keys, reverse=order == "desc")


def test_default_sort_is_by_name(client: TestClient, admin_headers: dict[str, str]) -> None:
    default = get(client, admin_headers)["data"]
    by_name = get(client, admin_headers, sort="name", order="asc")["data"]

    assert default == by_name


def test_pages_do_not_overlap(client: TestClient, admin_headers: dict[str, str]) -> None:
    pages = [get(client, admin_headers, page=page, pageSize=50)["data"] for page in (1, 2, 3, 4)]

    ids = [contact["id"] for page in pages for contact in page]
    assert len(ids) == len(set(ids)) == 180
    assert len(pages[3]) == 30


def test_page_past_the_end_is_empty(client: TestClient, admin_headers: dict[str, str]) -> None:
    body = get(client, admin_headers, page=99)

    assert body["data"] == []
    assert body["total"] == 180


def test_search_matches_name_email_or_company_ignoring_case(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    sample = SEED["contacts"][0]
    company_name = COMPANY_NAMES[sample["companyId"]]

    for query in (sample["name"].upper(), sample["email"].split("@")[0], company_name.lower()):
        ids = {contact["id"] for contact in all_pages(client, admin_headers, q=f"  {query} ")}
        assert sample["id"] in ids, query


def test_search_finds_accented_names_in_any_case(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    accented = next(c for c in SEED["contacts"] if any(ch in c["name"] for ch in "áéíóúâêôãõç"))

    ids = {c["id"] for c in all_pages(client, admin_headers, q=accented["name"].upper())}

    assert accented["id"] in ids


def test_search_treats_wildcards_as_text(client: TestClient, admin_headers: dict[str, str]) -> None:
    assert get(client, admin_headers, q="%")["total"] == 0
    assert get(client, admin_headers, q="_")["total"] == sum(
        "_" in c["email"] or "_" in c["name"] for c in SEED["contacts"]
    )


def test_seller_search_stays_inside_their_contacts(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    body = get(client, seller_headers, q=OTHERS_CONTACT["email"])

    assert body["total"] == 0


def test_filter_by_company(client: TestClient, admin_headers: dict[str, str]) -> None:
    company_id = SEED["contacts"][0]["companyId"]
    expected = {c["id"] for c in SEED["contacts"] if c["companyId"] == company_id}

    contacts = all_pages(client, admin_headers, companyId=company_id)

    assert {contact["id"] for contact in contacts} == expected


@pytest.mark.parametrize(
    "params",
    [{"sort": "phone"}, {"order": "up"}, {"page": 0}, {"pageSize": 0}, {"q": "x" * 101}],
    ids=["sort", "order", "page", "pageSize", "q"],
)
def test_invalid_parameters_are_422(
    client: TestClient, admin_headers: dict[str, str], params: dict[str, Any]
) -> None:
    response = client.get("/api/contacts", params=params, headers=admin_headers)

    assert response.status_code == 422
    assert response.json()["message"] == "Dados inválidos."


def test_list_requires_a_token(client: TestClient) -> None:
    assert client.get("/api/contacts").status_code == 401


def test_get_one_contact(client: TestClient, seller_headers: dict[str, str]) -> None:
    own = SELLER_CONTACTS[0]

    response = client.get(f"/api/contacts/{own['id']}", headers=seller_headers)

    assert response.status_code == 200
    assert response.json()["email"] == own["email"]
    assert response.json()["company"]["name"] == COMPANY_NAMES[own["companyId"]]


def test_someone_elses_contact_looks_missing_to_a_seller(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    response = client.get(f"/api/contacts/{OTHERS_CONTACT['id']}", headers=seller_headers)

    assert response.status_code == 404
    assert response.json() == {"message": "Contato não encontrado."}


def test_admin_can_open_any_contact(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get(f"/api/contacts/{OTHERS_CONTACT['id']}", headers=admin_headers)

    assert response.status_code == 200


def test_unknown_contact_is_404(client: TestClient, admin_headers: dict[str, str]) -> None:
    assert client.get("/api/contacts/ct_nope", headers=admin_headers).status_code == 404
