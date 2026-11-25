from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from crm_api.config import Settings, get_settings
from crm_api.models import Activity, Contact, Deal, User
from crm_api.security import create_access_token
from tests.conftest import ADMIN_EMAIL, SELLER_EMAIL

SESSION_EXPIRED = {"message": "Sessão expirada. Entre novamente."}
BAD_CREDENTIALS = {"message": "E-mail ou senha incorretos."}


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_a_token_and_the_user(client: TestClient, seeded: Session) -> None:
    response = client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": "demo1234"})

    assert response.status_code == 200
    body = response.json()
    assert body["user"] == {
        "id": "usr_1",
        "name": "Marina Albuquerque",
        "email": ADMIN_EMAIL,
        "role": "admin",
    }
    claims = jwt.decode(
        body["token"], get_settings().jwt_secret.get_secret_value(), algorithms=["HS256"]
    )
    assert claims["sub"] == "usr_1"
    assert claims["role"] == "admin"
    assert claims["exp"] - claims["iat"] == 8 * 60 * 60


def test_login_ignores_case_and_surrounding_spaces(client: TestClient, seeded: Session) -> None:
    response = client.post(
        "/api/auth/login", json={"email": "  Marina@MiniCRM.demo ", "password": "demo1234"}
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "credentials",
    [
        {"email": ADMIN_EMAIL, "password": "wrong-password"},
        {"email": "nobody@minicrm.demo", "password": "demo1234"},
    ],
    ids=["wrong password", "unknown e-mail"],
)
def test_bad_credentials_get_the_same_answer(
    client: TestClient, seeded: Session, credentials: dict[str, str]
) -> None:
    response = client.post("/api/auth/login", json=credentials)

    assert response.status_code == 401
    assert response.json() == BAD_CREDENTIALS


def test_invalid_login_body_is_a_422_with_a_message(client: TestClient, seeded: Session) -> None:
    response = client.post("/api/auth/login", json={"email": "not-an-email", "password": ""})

    assert response.status_code == 422
    body = response.json()
    assert body["message"] == "Dados inválidos."
    assert {error["field"] for error in body["errors"]} == {"email", "password"}


def test_token_endpoint_supports_the_docs_authorize_button(
    client: TestClient, seeded: Session
) -> None:
    response = client.post(
        "/api/auth/token", data={"username": SELLER_EMAIL, "password": "demo1234"}
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    me = client.get("/api/auth/me", headers=bearer(response.json()["access_token"]))
    assert me.json()["email"] == SELLER_EMAIL


def test_me_returns_the_signed_in_user(client: TestClient, seller_headers: dict[str, str]) -> None:
    response = client.get("/api/auth/me", headers=seller_headers)

    assert response.status_code == 200
    assert response.json() == {
        "id": "usr_2",
        "name": "Rafael Tavares",
        "email": SELLER_EMAIL,
        "role": "vendedor",
    }


def test_me_without_a_token_is_401(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json() == SESSION_EXPIRED
    assert response.headers["WWW-Authenticate"] == "Bearer"


def forged_tokens(user: User) -> dict[str, str]:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": user.id, "role": "admin", "iat": now, "exp": now + timedelta(hours=1)}
    other_secret = Settings(jwt_secret="another-secret-that-is-at-least-32-chars")
    return {
        "garbage": "not-a-jwt",
        "expired": create_access_token(user, settings, now=now - timedelta(hours=9)),
        "wrong secret": create_access_token(user, other_secret),
        "alg none": jwt.encode(payload, key=None, algorithm="none"),
        "no expiry": jwt.encode(
            {"sub": user.id, "iat": now}, settings.jwt_secret.get_secret_value(), "HS256"
        ),
    }


@pytest.mark.parametrize("kind", ["garbage", "expired", "wrong secret", "alg none", "no expiry"])
def test_invalid_tokens_are_rejected(client: TestClient, seeded: Session, kind: str) -> None:
    token = forged_tokens(seeded.get_one(User, "usr_2"))[kind]

    response = client.get("/api/auth/me", headers=bearer(token))

    assert response.status_code == 401
    assert response.json() == SESSION_EXPIRED


def test_token_of_a_deleted_user_is_rejected(client: TestClient, seeded: Session) -> None:
    user = seeded.get_one(User, "usr_2")
    token = create_access_token(user, get_settings())
    for model in (Activity, Deal, Contact):
        seeded.execute(delete(model).where(model.owner_id == user.id))
    seeded.delete(user)
    seeded.flush()

    response = client.get("/api/auth/me", headers=bearer(token))

    assert response.status_code == 401


def test_production_refuses_the_development_secret() -> None:
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(environment="production")


def test_production_accepts_a_long_random_secret() -> None:
    settings = Settings(environment="production", jwt_secret="x" * 40)

    assert settings.jwt_secret.get_secret_value() == "x" * 40
