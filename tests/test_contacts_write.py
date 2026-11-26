"""POST /api/contacts and PATCH /api/contacts/{id}."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from crm_api.seed import read_seed

SEED = read_seed()
COMPANY_NAMES = {company["id"]: company["name"] for company in SEED["companies"]}
SELLER_ID = "usr_2"
OWN = next(c for c in SEED["contacts"] if c["ownerId"] == SELLER_ID)
OTHERS = next(c for c in SEED["contacts"] if c["ownerId"] != SELLER_ID)
OTHER_COMPANY = next(c["id"] for c in SEED["companies"] if c["id"] != OWN["companyId"])

NEW = {
    "name": "Joana Prado",
    "email": "joana.prado@example.com",
    "phone": "(11) 91234-5678",
    "jobTitle": "Compradora",
    "companyId": "cmp_1",
}


def create(client: TestClient, headers: dict[str, str], **overrides: Any) -> Any:
    return client.post("/api/contacts", json={**NEW, **overrides}, headers=headers)


def test_create_contact(client: TestClient, seller_headers: dict[str, str]) -> None:
    response = create(client, seller_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["id"].startswith("ct_")
    assert body["ownerId"] == SELLER_ID  # belongs to whoever creates it
    assert body["company"] == {"id": "cmp_1", "name": COMPANY_NAMES["cmp_1"]}
    assert response.headers["Location"] == f"/api/contacts/{body['id']}"
    detail = client.get(response.headers["Location"], headers=seller_headers)
    assert detail.json() == body


def test_create_trims_and_lowercases(client: TestClient, seller_headers: dict[str, str]) -> None:
    response = create(
        client, seller_headers, name="  Joana Prado ", email=" Joana.PRADO@Example.com ", phone=" "
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Joana Prado"
    assert response.json()["email"] == "joana.prado@example.com"
    assert response.json()["phone"] == ""


def test_phone_and_job_title_are_optional(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    body = {key: NEW[key] for key in ("name", "email", "companyId")}

    response = client.post("/api/contacts", json=body, headers=seller_headers)

    assert response.status_code == 201
    assert response.json()["phone"] == ""
    assert response.json()["jobTitle"] == ""


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("name", "J", "Informe o nome (mínimo 2 letras)."),
        ("name", "x" * 101, "Nome muito longo."),
        ("email", "joana@", "Informe um e-mail válido."),
        ("phone", "1234", "Informe o telefone com DDD, por exemplo (11) 91234-5678."),
        ("jobTitle", "x" * 81, "Cargo muito longo."),
        ("companyId", "", "Escolha a empresa."),
    ],
)
def test_create_validates_like_the_front_end_form(
    client: TestClient, seller_headers: dict[str, str], field: str, value: str, message: str
) -> None:
    response = create(client, seller_headers, **{field: value})

    assert response.status_code == 422
    assert response.json()["message"] == message
    assert response.json()["errors"][0]["field"] == field


def test_missing_required_field_is_422(client: TestClient, seller_headers: dict[str, str]) -> None:
    response = client.post("/api/contacts", json={"name": "Joana"}, headers=seller_headers)

    assert response.status_code == 422
    assert response.json()["message"] == "Dados inválidos."


def test_unknown_company_is_422(client: TestClient, seller_headers: dict[str, str]) -> None:
    response = create(client, seller_headers, companyId="cmp_nope")

    assert response.status_code == 422
    assert response.json() == {"message": "Empresa não encontrada."}


def test_duplicate_email_is_409_ignoring_case(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    # Even an e-mail the seller can't see: e-mails are unique across the whole CRM.
    response = create(client, seller_headers, email=OTHERS["email"].upper())

    assert response.status_code == 409
    assert response.json() == {"message": "Já existe um contato com este e-mail."}


def test_create_requires_a_token(client: TestClient) -> None:
    assert client.post("/api/contacts", json=NEW).status_code == 401


def patch(client: TestClient, headers: dict[str, str], contact_id: str, **body: Any) -> Any:
    return client.patch(f"/api/contacts/{contact_id}", json=body, headers=headers)


def test_patch_changes_only_the_fields_sent(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    response = patch(client, seller_headers, OWN["id"], jobTitle="Diretora")

    assert response.status_code == 200
    body = response.json()
    assert body["jobTitle"] == "Diretora"
    assert body["name"] == OWN["name"]
    assert body["email"] == OWN["email"]
    assert body["ownerId"] == SELLER_ID


def test_patch_accepts_the_full_form(client: TestClient, seller_headers: dict[str, str]) -> None:
    # The front end sends every field, as with POST.
    response = patch(client, seller_headers, OWN["id"], **{**NEW, "email": OWN["email"]})

    assert response.status_code == 200
    assert response.json()["name"] == NEW["name"]


def test_patch_moving_company_returns_the_new_company_name(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    response = patch(client, seller_headers, OWN["id"], companyId=OTHER_COMPANY)

    assert response.json()["company"] == {"id": OTHER_COMPANY, "name": COMPANY_NAMES[OTHER_COMPANY]}


def test_patch_keeping_own_email_is_fine(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    response = patch(client, seller_headers, OWN["id"], email=OWN["email"].upper())

    assert response.status_code == 200


def test_patch_to_someone_elses_email_is_409(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    response = patch(client, seller_headers, OWN["id"], email=OTHERS["email"])

    assert response.status_code == 409


def test_patch_validates_fields(client: TestClient, seller_headers: dict[str, str]) -> None:
    response = patch(client, seller_headers, OWN["id"], name="J")

    assert response.status_code == 422
    assert response.json()["message"] == "Informe o nome (mínimo 2 letras)."


def test_patch_rejects_null(client: TestClient, seller_headers: dict[str, str]) -> None:
    response = patch(client, seller_headers, OWN["id"], name=None)

    assert response.status_code == 422
    assert response.json()["message"] == "Campos não podem ser nulos."


def test_patch_unknown_company_is_422(client: TestClient, seller_headers: dict[str, str]) -> None:
    response = patch(client, seller_headers, OWN["id"], companyId="cmp_nope")

    assert response.json() == {"message": "Empresa não encontrada."}


def test_empty_patch_changes_nothing(client: TestClient, seller_headers: dict[str, str]) -> None:
    before = client.get(f"/api/contacts/{OWN['id']}", headers=seller_headers).json()

    response = patch(client, seller_headers, OWN["id"])

    assert response.status_code == 200
    assert response.json() == before


def test_seller_cannot_patch_someone_elses_contact(
    client: TestClient, seller_headers: dict[str, str]
) -> None:
    response = patch(client, seller_headers, OTHERS["id"], jobTitle="Hacker")

    assert response.status_code == 404
    assert response.json() == {"message": "Contato não encontrado."}


def test_admin_can_patch_any_contact_without_taking_it(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = patch(client, admin_headers, OTHERS["id"], jobTitle="Gerente")

    assert response.status_code == 200
    assert response.json()["ownerId"] == OTHERS["ownerId"]


def test_owner_cannot_be_changed(client: TestClient, seller_headers: dict[str, str]) -> None:
    response = patch(client, seller_headers, OWN["id"], ownerId="usr_1")

    assert response.status_code == 200
    assert response.json()["ownerId"] == SELLER_ID  # unknown fields are ignored


def test_simultaneous_duplicate_is_still_409(
    client: TestClient, seller_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulate two requests passing the e-mail check at the same time: the database's unique
    # constraint is the last line of defense.
    from crm_api.routers import contacts

    monkeypatch.setattr(contacts, "_check_rules", lambda *_args, **_kwargs: None)

    response = create(client, seller_headers, email=OTHERS["email"])

    assert response.status_code == 409
    assert client.get("/api/auth/me", headers=seller_headers).status_code == 200  # session usable
