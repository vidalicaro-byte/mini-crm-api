"""GET /api/activities?contactId=."""

from fastapi.testclient import TestClient

from crm_api.seed import read_seed

SEED = read_seed()
SELLER_ID = "usr_2"
OWN_CONTACT = next(
    c["id"]
    for c in SEED["contacts"]
    if c["ownerId"] == SELLER_ID and any(a["contactId"] == c["id"] for a in SEED["activities"])
)
OTHERS_CONTACT = next(c["id"] for c in SEED["contacts"] if c["ownerId"] != SELLER_ID)


def test_activities_of_a_contact_newest_first(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    response = client.get(
        "/api/activities", params={"contactId": OWN_CONTACT}, headers=seller_headers
    )

    assert response.status_code == 200
    body = response.json()
    expected = {a["id"] for a in SEED["activities"] if a["contactId"] == OWN_CONTACT}
    assert {a["id"] for a in body["data"]} == expected
    assert body["total"] == len(expected)
    dates = [a["date"] for a in body["data"]]
    assert dates == sorted(dates, reverse=True)
    assert set(body["data"][0]) == {
        "id",
        "type",
        "contactId",
        "dealId",
        "ownerId",
        "date",
        "summary",
    }


def test_contact_is_required(client: TestClient, seller_headers: dict[str, str]) -> None:
    response = client.get("/api/activities", headers=seller_headers)

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "contactId"


def test_activities_of_someone_elses_contact_are_404(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    response = client.get(
        "/api/activities", params={"contactId": OTHERS_CONTACT}, headers=seller_headers
    )

    assert response.status_code == 404


def test_admin_sees_any_contacts_activities(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get(
        "/api/activities", params={"contactId": OTHERS_CONTACT}, headers=admin_headers
    )

    assert response.status_code == 200


def test_activities_require_a_token(client: TestClient) -> None:
    assert client.get("/api/activities", params={"contactId": OWN_CONTACT}).status_code == 401
