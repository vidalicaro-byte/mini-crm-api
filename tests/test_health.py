from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_schema_is_published(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Mini-CRM API"
    assert "/health" in schema["paths"]


def test_docs_offer_the_authorize_button(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    scheme = schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    assert scheme["flows"]["password"]["tokenUrl"] == "/api/auth/token"


def test_head_requests_are_accepted(client: TestClient) -> None:
    # Render and uptime monitors probe with HEAD.
    assert client.head("/health").status_code == 200
    assert client.head("/", follow_redirects=False).status_code == 307


def test_error_responses_are_documented_with_their_own_examples(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    patch = schema["paths"]["/api/contacts/{contact_id}"]["patch"]["responses"]
    examples = {
        code: r["content"]["application/json"]["example"]
        for code, r in patch.items()
        if code != "200"
    }
    assert examples["401"]["message"] == "Sessão expirada. Entre novamente."
    assert examples["409"]["message"] == "Já existe um contato com este e-mail."
    assert examples["422"]["errors"][0]["field"] == "email"
    assert patch["422"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ValidationErrorResponse"
    )
