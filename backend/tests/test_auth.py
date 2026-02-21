import pytest
from httpx import ASGITransport, AsyncClient

from backend.tests.conftest import auth_header


class TestBootstrap:
    async def test_bootstrap_creates_principal_and_credentials(self, client: AsyncClient):
        resp = await client.post("/dev/bootstrap", json={
            "display_name": "Test",
            "num_credentials": 4,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["principal"]["display_name"] == "Test"
        assert len(data["credentials"]) == 4
        for cred in data["credentials"]:
            assert "client_id" in cred
            assert "client_secret" in cred

    async def test_bootstrap_default_values(self, client: AsyncClient):
        resp = await client.post("/dev/bootstrap", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["principal"]["display_name"] == "Dev Principal"
        assert len(data["credentials"]) == 4


class TestTokenExchange:
    async def test_valid_credentials(self, client: AsyncClient):
        bootstrap = await client.post("/dev/bootstrap", json={"num_credentials": 1})
        cred = bootstrap.json()["credentials"][0]

        resp = await client.post("/api/token", json={
            "client_id": cred["client_id"],
            "client_secret": cred["client_secret"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_invalid_credentials(self, client: AsyncClient):
        resp = await client.post("/api/token", json={
            "client_id": "fake_id",
            "client_secret": "fake_secret",
        })
        assert resp.status_code == 401


class TestCredentialCRUD:
    async def test_list_credentials(self, bootstrapped, client: AsyncClient):
        resp = await client.get(
            "/api/credentials",
            headers=auth_header(bootstrapped["tokens"][0]),
        )
        assert resp.status_code == 200
        creds = resp.json()
        assert len(creds) == 4

    async def test_create_credential(self, bootstrapped, client: AsyncClient):
        resp = await client.post(
            "/api/credentials?display_name=New+Agent",
            headers=auth_header(bootstrapped["tokens"][0]),
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "New Agent"

    async def test_delete_credential(self, bootstrapped, client: AsyncClient):
        token = bootstrapped["tokens"][0]
        cred_id = bootstrapped["credentials"][1]["credential_id"]

        resp = await client.delete(
            f"/api/credentials/{cred_id}",
            headers=auth_header(token),
        )
        assert resp.status_code == 204

        # Verify it's gone
        resp = await client.get("/api/credentials", headers=auth_header(token))
        ids = [c["credential_id"] for c in resp.json()]
        assert cred_id not in ids

    async def test_delete_nonexistent_credential(self, bootstrapped, client: AsyncClient):
        resp = await client.delete(
            "/api/credentials/nonexistent",
            headers=auth_header(bootstrapped["tokens"][0]),
        )
        assert resp.status_code == 404


class TestAuthProtection:
    async def test_no_token_rejected(self, client: AsyncClient):
        resp = await client.get("/api/credentials")
        assert resp.status_code in (401, 403)

    async def test_invalid_token_rejected(self, client: AsyncClient):
        resp = await client.get(
            "/api/credentials",
            headers=auth_header("invalid.token.here"),
        )
        assert resp.status_code == 401
