from fastapi.testclient import TestClient


def test_admin_lists_every_user_sorted_by_name(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get("/api/users", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert body["page"] == 1
    assert body["pageSize"] == 20
    names = [user["name"] for user in body["data"]]
    assert names == sorted(names)
    assert all("passwordHash" not in user and "password_hash" not in user for user in body["data"])


def test_users_are_paginated(client: TestClient, admin_headers: dict[str, str]) -> None:
    first = client.get("/api/users?page=1&pageSize=2", headers=admin_headers).json()
    third = client.get("/api/users?page=3&pageSize=2", headers=admin_headers).json()

    assert len(first["data"]) == 2
    assert len(third["data"]) == 1
    assert third["total"] == 5


def test_page_size_above_100_is_rejected(client: TestClient, admin_headers: dict[str, str]) -> None:
    response = client.get("/api/users?pageSize=101", headers=admin_headers)

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "pageSize"


def test_sellers_cannot_list_users(client: TestClient, seller_headers: dict[str, str]) -> None:
    response = client.get("/api/users", headers=seller_headers)

    assert response.status_code == 403
    assert response.json() == {"message": "Você não tem permissão para acessar este recurso."}


def test_listing_users_requires_a_token(client: TestClient) -> None:
    assert client.get("/api/users").status_code == 401
