"""Tests for Phase 3: Management UI (profile, admin, conventions)."""

import shutil
from pathlib import Path

import pytest
from httpx import AsyncClient

from backend.auth.service import create_principal, create_token, get_principal, list_all_principals
from backend.engine.conventions import list_conventions, _conventions
from backend.engine.persistence import DATA_DIR
from backend.models.seat import PlayerKind
from backend.tests.conftest import auth_header


def _human_token(principal) -> str:
    """Create a human token for a principal (no credential_id)."""
    resp = create_token(principal.identity_id, None, PlayerKind.HUMAN)
    return resp.access_token


@pytest.fixture(autouse=True)
def clean_persistence():
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    yield
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)


@pytest.fixture(autouse=True)
def reset_conventions():
    """Restore built-in conventions between tests."""
    from backend.engine.conventions import _seed_builtins
    _conventions.clear()
    _seed_builtins()
    yield


# ---------------------------------------------------------------------------
# Auth Service Extensions
# ---------------------------------------------------------------------------

class TestAuthServiceExtensions:
    def test_first_principal_is_admin(self):
        p1 = create_principal("First")
        assert p1.is_admin is True

    def test_second_principal_not_admin(self):
        create_principal("First")
        p2 = create_principal("Second")
        assert p2.is_admin is False

    def test_list_all_principals(self):
        create_principal("A")
        create_principal("B")
        assert len(list_all_principals()) == 2

    def test_update_principal_name(self):
        from backend.auth.service import update_principal_name
        p = create_principal("Old")
        updated = update_principal_name(p.identity_id, "New")
        assert updated is not None
        assert updated.display_name == "New"
        assert get_principal(p.identity_id).display_name == "New"

    def test_update_nonexistent_returns_none(self):
        from backend.auth.service import update_principal_name
        assert update_principal_name("fake", "X") is None

    def test_delete_principal(self):
        from backend.auth.service import delete_principal, create_credential, list_credentials
        p = create_principal("Del")
        create_credential(p.identity_id, "Agent 1")
        assert len(list_credentials(p.identity_id)) == 1
        assert delete_principal(p.identity_id) is True
        assert get_principal(p.identity_id) is None
        # Credentials should also be gone
        assert len(list_credentials(p.identity_id)) == 0

    def test_delete_nonexistent(self):
        from backend.auth.service import delete_principal
        assert delete_principal("fake") is False

    def test_force_revoke_credential(self):
        from backend.auth.service import create_credential, force_revoke_credential, list_credentials
        p = create_principal("FR")
        cred = create_credential(p.identity_id, "Agent")
        assert force_revoke_credential(cred.credential_id) is True
        assert len(list_credentials(p.identity_id)) == 0

    def test_force_revoke_nonexistent(self):
        from backend.auth.service import force_revoke_credential
        assert force_revoke_credential("fake") is False


# ---------------------------------------------------------------------------
# Profile Endpoints
# ---------------------------------------------------------------------------

class TestProfileEndpoints:
    async def test_get_profile(self, client: AsyncClient):
        p = create_principal("ProfileUser")
        token = _human_token(p)
        resp = await client.get("/api/profile", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "ProfileUser"
        assert data["is_admin"] is True  # first principal
        assert data["credential_count"] == 0

    async def test_update_profile(self, client: AsyncClient):
        p = create_principal("Old Name")
        token = _human_token(p)
        resp = await client.patch(
            "/api/profile",
            json={"display_name": "New Name"},
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "New Name"

    async def test_data_export_empty(self, client: AsyncClient):
        p = create_principal("Exporter")
        token = _human_token(p)
        resp = await client.get("/api/profile/data-export", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["total_tables"] == 0

    async def test_delete_account(self, client: AsyncClient):
        p = create_principal("Deletable")
        token = _human_token(p)
        resp = await client.delete("/api/profile", headers=auth_header(token))
        assert resp.status_code == 204
        assert get_principal(p.identity_id) is None


# ---------------------------------------------------------------------------
# Admin Endpoints
# ---------------------------------------------------------------------------

class TestAdminEndpoints:
    async def test_list_principals(self, client: AsyncClient):
        admin = create_principal("Admin")
        create_principal("User2")
        token = _human_token(admin)
        resp = await client.get("/api/admin/principals", headers=auth_header(token))
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_non_admin_forbidden(self, client: AsyncClient):
        create_principal("Admin")  # first = admin
        user = create_principal("Regular")
        token = _human_token(user)
        resp = await client.get("/api/admin/principals", headers=auth_header(token))
        assert resp.status_code == 403

    async def test_delete_principal(self, client: AsyncClient):
        admin = create_principal("Admin")
        user = create_principal("ToDelete")
        token = _human_token(admin)
        resp = await client.delete(
            f"/api/admin/principals/{user.identity_id}",
            headers=auth_header(token),
        )
        assert resp.status_code == 204
        assert get_principal(user.identity_id) is None

    async def test_list_all_credentials(self, client: AsyncClient):
        from backend.auth.service import create_credential
        admin = create_principal("Admin")
        create_credential(admin.identity_id, "Agent 1")
        token = _human_token(admin)
        resp = await client.get("/api/admin/credentials", headers=auth_header(token))
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_force_revoke_credential(self, client: AsyncClient):
        from backend.auth.service import create_credential
        admin = create_principal("Admin")
        cred = create_credential(admin.identity_id, "Agent")
        token = _human_token(admin)
        resp = await client.delete(
            f"/api/admin/credentials/{cred.credential_id}",
            headers=auth_header(token),
        )
        assert resp.status_code == 204

    async def test_research_health(self, client: AsyncClient):
        admin = create_principal("Admin")
        token = _human_token(admin)
        resp = await client.get("/api/admin/research/health", headers=auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "active_tables" in data
        assert "persisted_sessions" in data


# ---------------------------------------------------------------------------
# Convention Templates
# ---------------------------------------------------------------------------

class TestConventionEndpoints:
    async def test_list_conventions(self, client: AsyncClient):
        p = create_principal("User")
        token = _human_token(p)
        resp = await client.get("/api/conventions", headers=auth_header(token))
        assert resp.status_code == 200
        templates = resp.json()
        assert len(templates) == 2  # Euchre + Pinochle built-ins
        names = [t["name"] for t in templates]
        assert "Euchre - Standard" in names
        assert "Double Pinochle" in names

    async def test_get_convention_by_id(self, client: AsyncClient):
        p = create_principal("User")
        token = _human_token(p)
        resp = await client.get("/api/conventions/builtin_euchre", headers=auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["name"] == "Euchre - Standard"

    async def test_get_nonexistent(self, client: AsyncClient):
        p = create_principal("User")
        token = _human_token(p)
        resp = await client.get("/api/conventions/fake", headers=auth_header(token))
        assert resp.status_code == 404

    async def test_create_convention_admin_only(self, client: AsyncClient):
        admin = create_principal("Admin")
        token = _human_token(admin)
        resp = await client.post(
            "/api/conventions",
            json={"name": "Custom Game", "deck_recipe": "standard_52", "seat_count": 2},
            headers=auth_header(token),
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Custom Game"
        assert resp.json()["built_in"] is False

    async def test_create_convention_non_admin_forbidden(self, client: AsyncClient):
        create_principal("Admin")
        user = create_principal("Regular")
        token = _human_token(user)
        resp = await client.post(
            "/api/conventions",
            json={"name": "Nope", "deck_recipe": "standard_52", "seat_count": 2},
            headers=auth_header(token),
        )
        assert resp.status_code == 403

    async def test_update_custom_convention(self, client: AsyncClient):
        from backend.engine.conventions import create_convention as create_conv
        from backend.models.convention import ConventionCreate
        template = create_conv(ConventionCreate(name="Old", deck_recipe="standard_52", seat_count=2))
        admin = create_principal("Admin")
        token = _human_token(admin)
        resp = await client.put(
            f"/api/conventions/{template.template_id}",
            json={"name": "Updated"},
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    async def test_cannot_update_builtin(self, client: AsyncClient):
        admin = create_principal("Admin")
        token = _human_token(admin)
        resp = await client.put(
            "/api/conventions/builtin_euchre",
            json={"name": "Hacked"},
            headers=auth_header(token),
        )
        assert resp.status_code == 404

    async def test_delete_custom_convention(self, client: AsyncClient):
        from backend.engine.conventions import create_convention as create_conv
        from backend.models.convention import ConventionCreate
        template = create_conv(ConventionCreate(name="Del", deck_recipe="standard_52", seat_count=2))
        admin = create_principal("Admin")
        token = _human_token(admin)
        resp = await client.delete(
            f"/api/conventions/{template.template_id}",
            headers=auth_header(token),
        )
        assert resp.status_code == 204

    async def test_cannot_delete_builtin(self, client: AsyncClient):
        admin = create_principal("Admin")
        token = _human_token(admin)
        resp = await client.delete(
            "/api/conventions/builtin_euchre",
            headers=auth_header(token),
        )
        assert resp.status_code == 404
