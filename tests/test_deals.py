"""GET /api/deals and PATCH /api/deals/{id}."""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from crm_api.seed import read_seed

SEED = read_seed()
SELLER_ID = "usr_2"
CONTACT_NAMES = {contact["id"]: contact["name"] for contact in SEED["contacts"]}
COMPANY_NAMES = {company["id"]: company["name"] for company in SEED["companies"]}
SELLER_DEALS = [d for d in SEED["deals"] if d["ownerId"] == SELLER_ID]
OWN_OPEN = next(d for d in SELLER_DEALS if d["closedAt"] is None)
OWN_WON = next(d for d in SELLER_DEALS if d["stage"] == "ganho")
OTHERS_DEAL = next(d for d in SEED["deals"] if d["ownerId"] != SELLER_ID)
OTHERS_CONTACT = next(c for c in SEED["contacts"] if c["ownerId"] != SELLER_ID)


def get(client: TestClient, headers: dict[str, str], **params: Any) -> dict[str, Any]:
    response = client.get("/api/deals", params=params, headers=headers)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def test_board_gets_every_visible_deal_in_one_page(
    client: TestClient, admin_headers: dict[str, str], seller_headers: dict[str, str]
) -> None:
    everything = get(client, admin_headers)
    own = get(client, seller_headers)

    assert everything["total"] == len(everything["data"]) == len(SEED["deals"])
    assert everything["pageSize"] == 200
    assert {deal["id"] for deal in own["data"]} == {deal["id"] for deal in SELLER_DEALS}


def test_deals_are_newest_first(client: TestClient, admin_headers: dict[str, str]) -> None:
    dates = [deal["createdAt"] for deal in get(client, admin_headers)["data"]]

    assert dates == sorted(dates, reverse=True)


def test_deal_has_the_contract_shape(client: TestClient, admin_headers: dict[str, str]) -> None:
    deal = get(client, admin_headers, pageSize=1)["data"][0]

    assert set(deal) == {
        "id",
        "title",
        "value",
        "stage",
        "contactId",
        "companyId",
        "ownerId",
        "createdAt",
        "expectedCloseDate",
        "closedAt",
        "contact",
        "company",
    }
    assert deal["contact"] == {"id": deal["contactId"], "name": CONTACT_NAMES[deal["contactId"]]}
    assert deal["company"] == {"id": deal["companyId"], "name": COMPANY_NAMES[deal["companyId"]]}


def test_deals_of_a_contact(client: TestClient, seller_headers: dict[str, str]) -> None:
    contact_id = OWN_OPEN["contactId"]

    deals = get(client, seller_headers, contactId=contact_id)["data"]

    assert {d["id"] for d in deals} == {
        d["id"] for d in SEED["deals"] if d["contactId"] == contact_id
    }


def test_deals_of_someone_elses_contact_are_404(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    response = client.get(
        "/api/deals", params={"contactId": OTHERS_CONTACT["id"]}, headers=seller_headers
    )

    assert response.status_code == 404
    assert response.json() == {"message": "Contato não encontrado."}


def test_deals_of_a_company_only_count_visible_ones(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    company_id = OWN_OPEN["companyId"]

    deals = get(client, seller_headers, companyId=company_id)["data"]

    assert {d["id"] for d in deals} == {
        d["id"] for d in SELLER_DEALS if d["companyId"] == company_id
    }


def test_page_size_is_capped_at_200(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get("/api/deals", params={"pageSize": 201}, headers=admin_headers)

    assert response.status_code == 422


def move(client: TestClient, headers: dict[str, str], deal_id: str, stage: Any) -> Any:
    return client.patch(f"/api/deals/{deal_id}", json={"stage": stage}, headers=headers)


def test_moving_between_open_stages_keeps_closed_at_empty(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    response = move(client, seller_headers, OWN_OPEN["id"], "negociacao")

    assert response.status_code == 200
    assert response.json()["stage"] == "negociacao"
    assert response.json()["closedAt"] is None


@pytest.mark.parametrize("stage", ["ganho", "perdido"])
def test_closing_a_deal_stamps_closed_at(
    client: TestClient, seller_headers: dict[str, str], stage: str
) -> None:
    before = datetime.now(UTC)

    response = move(client, seller_headers, OWN_OPEN["id"], stage)

    closed_at = datetime.fromisoformat(response.json()["closedAt"])
    assert before <= closed_at <= datetime.now(UTC)


def test_switching_between_won_and_lost_keeps_the_closing_date(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    original = get(client, seller_headers, contactId=OWN_WON["contactId"])["data"]
    closed_at = next(d["closedAt"] for d in original if d["id"] == OWN_WON["id"])

    response = move(client, seller_headers, OWN_WON["id"], "perdido")

    assert response.json()["closedAt"] == closed_at


def test_reopening_a_deal_clears_closed_at(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    response = move(client, seller_headers, OWN_WON["id"], "proposta")

    assert response.json()["closedAt"] is None


def test_move_persists(client: TestClient, seller_headers: dict[str, str]) -> None:
    move(client, seller_headers, OWN_OPEN["id"], "proposta")

    deals = get(client, seller_headers)["data"]

    assert next(d for d in deals if d["id"] == OWN_OPEN["id"])["stage"] == "proposta"


@pytest.mark.parametrize("stage", ["fechado", None, 3])
def test_invalid_stage_is_422(
    client: TestClient, seller_headers: dict[str, str], stage: Any
) -> None:
    response = move(client, seller_headers, OWN_OPEN["id"], stage)

    assert response.status_code == 422
    assert response.json()["message"] == "Etapa inválida."


def test_seller_cannot_move_someone_elses_deal(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    response = move(client, seller_headers, OTHERS_DEAL["id"], "ganho")

    assert response.status_code == 404
    assert response.json() == {"message": "Negócio não encontrado."}


def test_admin_can_move_any_deal(client: TestClient, admin_headers: dict[str, str]) -> None:
    assert move(client, admin_headers, OTHERS_DEAL["id"], "contato").status_code == 200


def test_deals_require_a_token(client: TestClient) -> None:
    assert client.get("/api/deals").status_code == 401
    assert client.patch(f"/api/deals/{OWN_OPEN['id']}", json={"stage": "ganho"}).status_code == 401
