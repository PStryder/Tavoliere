import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import create_app


def _clear_state():
    """Reset all in-memory stores between tests."""
    import backend.engine.table_manager as tm
    import backend.auth.service as auth
    import backend.engine.state as st
    import backend.engine.action_engine as ae
    import backend.engine.consensus as cons
    import backend.engine.optimistic as opt
    tm._tables.clear()
    auth._principals.clear()
    auth._credentials.clear()
    auth._credentials_by_client_id.clear()
    st._table_states.clear()
    ae.get_rate_limiter().clear()
    cons._pending_actions.clear()
    opt.clear_optimistic("")  # clear all
    opt._optimistic_actions.clear()


@pytest.fixture(autouse=True)
def clean_state():
    _clear_state()
    yield
    _clear_state()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def bootstrapped(client: AsyncClient):
    """Bootstrap a principal with 4 AI credentials and return tokens."""
    resp = await client.post("/dev/bootstrap", json={
        "display_name": "Test Principal",
        "num_credentials": 4,
        "credential_prefix": "Test Agent",
    })
    assert resp.status_code == 200
    data = resp.json()

    tokens = []
    for cred in data["credentials"]:
        token_resp = await client.post("/api/token", json={
            "client_id": cred["client_id"],
            "client_secret": cred["client_secret"],
        })
        assert token_resp.status_code == 200
        tokens.append(token_resp.json()["access_token"])

    return {
        "principal": data["principal"],
        "credentials": data["credentials"],
        "tokens": tokens,
    }


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
