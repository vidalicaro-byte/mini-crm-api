"""GET /api/companies and /api/companies/{id}. Expected figures are computed from the seed file."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from crm_api.seed import read_seed
from crm_api.text import collation_key

SEED = read_seed()
SELLER_ID = "usr_2"
SIZE_RANK = {"pequena": 0, "media": 1, "grande": 2}


def expected_figures(company_id: str, owner: str | None) -> dict[str, Any]:
    """What the mock API computes: a seller (owner) only counts their own records."""

    def mine(record: dict[str, Any]) -> bool:
        return owner is None or record["ownerId"] == owner

    contacts = [c for c in SEED["contacts"] if c["companyId"] == company_id and mine(c)]
    open_deals = [
        d
        for d in SEED["deals"]
        if d["companyId"] == company_id and mine(d) and d["stage"] not in ("ganho", "perdido")
    ]
    return {
        "contactsCount": len(contacts),
        "openDeals": {"count": len(open_deals), "value": sum(d["value"] for d in open_deals)},
    }


def get(client: TestClient, headers: dict[str, str], **params: Any) -> dict[str, Any]:
    response = client.get("/api/companies", params={"pageSize": 100, **params}, headers=headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def test_everyone_sees_every_company(
    client: TestClient, admin_headers: dict[str, str], seller_headers: dict[str, str]
) -> None:
    assert get(client, admin_headers)["total"] == len(SEED["companies"])
    assert get(client, seller_headers)["total"] == len(SEED["companies"])


@pytest.mark.parametrize("viewer", ["admin", "seller"])
def test_figures_count_only_what_the_viewer_may_see(
    client: TestClient,
    admin_headers: dict[str, str],
    seller_headers: dict[str, str],
    viewer: str,
) -> None:
    headers, owner = (admin_headers, None) if viewer == "admin" else (seller_headers, SELLER_ID)

    for company in get(client, headers)["data"]:
        figures = {key: company[key] for key in ("contactsCount", "openDeals")}
        assert figures == expected_figures(company["id"], owner), company["id"]


def test_company_has_the_contract_shape(client: TestClient, admin_headers: dict[str, str]) -> None:
    company = get(client, admin_headers, pageSize=1)["data"][0]

    seed_company = next(c for c in SEED["companies"] if c["id"] == company["id"])
    assert company == {**seed_company, **expected_figures(company["id"], None)}


def sort_key(sort: str, company: dict[str, Any]) -> Any:
    if sort == "size":
        return SIZE_RANK[company["size"]]
    if sort == "contactsCount":
        return company["contactsCount"]
    if sort == "openDealsValue":
        return company["openDeals"]["value"]
    return collation_key(company[sort])  # name, industry, city


@pytest.mark.parametrize(
    "sort", ["name", "industry", "size", "city", "contactsCount", "openDealsValue"]
)
@pytest.mark.parametrize("order", ["asc", "desc"])
def test_companies_are_sorted(
    client: TestClient, seller_headers: dict[str, str], sort: str, order: str
) -> None:
    companies = get(client, seller_headers, sort=sort, order=order)["data"]

    keys = [sort_key(sort, company) for company in companies]
    assert keys == sorted(keys, reverse=order == "desc")


def test_ties_are_broken_by_name(client: TestClient, admin_headers: dict[str, str]) -> None:
    companies = get(client, admin_headers, sort="size")["data"]

    for size in SIZE_RANK:
        names = [c["name"] for c in companies if c["size"] == size]
        assert names == sorted(names, key=collation_key)


def test_filter_by_size(client: TestClient, admin_headers: dict[str, str]) -> None:
    companies = get(client, admin_headers, size="grande")["data"]

    assert {c["id"] for c in companies} == {
        c["id"] for c in SEED["companies"] if c["size"] == "grande"
    }


def test_search_matches_name_industry_or_city(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    sample = SEED["companies"][0]

    for query in (sample["name"].upper(), sample["industry"].lower(), sample["city"]):
        ids = {c["id"] for c in get(client, admin_headers, q=query)["data"]}
        assert sample["id"] in ids, query


@pytest.mark.parametrize("params", [{"size": "enorme"}, {"sort": "state"}])
def test_invalid_parameters_are_422(
    client: TestClient, admin_headers: dict[str, str], params: dict[str, str]
) -> None:
    response = client.get("/api/companies", params=params, headers=admin_headers)

    assert response.status_code == 422


def test_get_one_company_with_seller_figures(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    company_id = SEED["companies"][0]["id"]

    response = client.get(f"/api/companies/{company_id}", headers=seller_headers)

    assert response.status_code == 200
    assert (
        response.json()["contactsCount"] == expected_figures(company_id, SELLER_ID)["contactsCount"]
    )


def test_unknown_company_is_404(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get("/api/companies/cmp_nope", headers=admin_headers)

    assert response.status_code == 404
    assert response.json() == {"message": "Empresa não encontrada."}


def test_companies_require_a_token(client: TestClient) -> None:
    assert client.get("/api/companies").status_code == 401
