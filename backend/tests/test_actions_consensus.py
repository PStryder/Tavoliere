import pytest
from httpx import AsyncClient

from backend.tests.conftest import auth_header


async def _setup_table_with_players(client: AsyncClient, tokens: list[str]):
    """Create a table, seat 4 players, shuffle deck. Returns table_id."""
    resp = await client.post(
        "/api/tables",
        json={"display_name": "Test", "deck_recipe": "euchre_24"},
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


def _get_deck_cards(table_data: dict) -> list[str]:
    for z in table_data["zones"]:
        if z["zone_id"] == "deck":
            return z["card_ids"]
    return []


class TestMoveCard:
    async def test_move_card_requires_consensus(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        # Get a card from the deck
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        deck_cards = _get_deck_cards(resp.json())
        card_id = deck_cards[0]

        # Submit move: deck -> center
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "move_card",
                "card_ids": [card_id],
                "source_zone_id": "deck",
                "target_zone_id": "center",
            },
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"
        action_id = resp.json()["action_id"]
        assert action_id

    async def test_consensus_full_cycle(self, client: AsyncClient, bootstrapped):
        """Intent -> 3 ACKs -> committed."""
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        card_id = _get_deck_cards(resp.json())[0]

        # Submit intent
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "move_card",
                "card_ids": [card_id],
                "source_zone_id": "deck",
                "target_zone_id": "center",
            },
            headers=auth_header(tokens[0]),
        )
        action_id = resp.json()["action_id"]

        # ACK from seats 1, 2, 3
        for token in tokens[1:]:
            resp = await client.post(
                f"/api/tables/{table_id}/actions/{action_id}/ack",
                headers=auth_header(token),
            )
            assert resp.status_code == 200

        # Last ACK should trigger commit
        assert resp.json()["status"] == "committed"

        # Verify the card moved
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        data = resp.json()
        center_cards = []
        deck_cards = []
        for z in data["zones"]:
            if z["zone_id"] == "center":
                center_cards = z["card_ids"]
            elif z["zone_id"] == "deck":
                deck_cards = z["card_ids"]

        assert card_id in center_cards
        assert card_id not in deck_cards


class TestDealRoundRobin:
    async def test_deal_to_hands(self, client: AsyncClient, bootstrapped):
        """Deal cards round-robin to all hands."""
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        # Get first 20 cards from deck (5 per player)
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        deck_cards = _get_deck_cards(resp.json())[:20]

        target_zones = [f"hand_seat_{i}" for i in range(4)]

        # Submit deal intent
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "deal_round_robin",
                "card_ids": deck_cards,
                "source_zone_id": "deck",
                "target_zone_ids": target_zones,
            },
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 200
        action_id = resp.json()["action_id"]

        # All other seats ACK
        for token in tokens[1:]:
            resp = await client.post(
                f"/api/tables/{table_id}/actions/{action_id}/ack",
                headers=auth_header(token),
            )

        assert resp.json()["status"] == "committed"

        # Verify each hand has 5 cards
        for i, token in enumerate(tokens):
            resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(token))
            zones = resp.json()["zones"]
            for z in zones:
                if z["zone_id"] == f"hand_seat_{i}":
                    assert len(z["card_ids"]) == 5
                    break

        # Verify deck lost 20 cards
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        remaining = _get_deck_cards(resp.json())
        assert len(remaining) == 4  # 24 - 20 = 4


class TestNackAndDispute:
    async def test_nack_triggers_dispute(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        card_id = _get_deck_cards(resp.json())[0]

        # Submit intent
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "move_card",
                "card_ids": [card_id],
                "source_zone_id": "deck",
                "target_zone_id": "center",
            },
            headers=auth_header(tokens[0]),
        )
        action_id = resp.json()["action_id"]

        # NACK from seat 1
        resp = await client.post(
            f"/api/tables/{table_id}/actions/{action_id}/nack",
            json={"reason": "turn", "reason_text": "Not your turn!"},
            headers=auth_header(tokens[1]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

        # Table should be in dispute mode
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        assert resp.json()["dispute_active"] is True

    async def test_dispute_blocks_new_consensus(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        deck = _get_deck_cards(resp.json())

        # Create and NACK an intent
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "move_card",
                "card_ids": [deck[0]],
                "source_zone_id": "deck",
                "target_zone_id": "center",
            },
            headers=auth_header(tokens[0]),
        )
        action_id = resp.json()["action_id"]
        await client.post(
            f"/api/tables/{table_id}/actions/{action_id}/nack",
            json={},
            headers=auth_header(tokens[1]),
        )

        # Try to submit another consensus action — should be rejected
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "move_card",
                "card_ids": [deck[1]],
                "source_zone_id": "deck",
                "target_zone_id": "center",
            },
            headers=auth_header(tokens[2]),
        )
        assert resp.json()["status"] == "rejected"
        assert "dispute" in resp.json()["reason"].lower()

    async def test_resolve_dispute(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        card_id = _get_deck_cards(resp.json())[0]

        # Create, NACK, then resolve
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "move_card",
                "card_ids": [card_id],
                "source_zone_id": "deck",
                "target_zone_id": "center",
            },
            headers=auth_header(tokens[0]),
        )
        action_id = resp.json()["action_id"]
        await client.post(
            f"/api/tables/{table_id}/actions/{action_id}/nack",
            json={},
            headers=auth_header(tokens[1]),
        )

        # Resolve dispute
        resp = await client.post(
            f"/api/tables/{table_id}/dispute/resolve",
            json={"resolution": "cancelled"},
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 200

        # Table should no longer be in dispute
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        assert resp.json()["dispute_active"] is False


class TestPendingLimit:
    async def test_one_pending_per_seat(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        deck = _get_deck_cards(resp.json())

        # First intent — should be pending
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "move_card",
                "card_ids": [deck[0]],
                "source_zone_id": "deck",
                "target_zone_id": "center",
            },
            headers=auth_header(tokens[0]),
        )
        assert resp.json()["status"] == "pending"

        # Second intent from same seat — should be rejected
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "move_card",
                "card_ids": [deck[1]],
                "source_zone_id": "deck",
                "target_zone_id": "center",
            },
            headers=auth_header(tokens[0]),
        )
        assert resp.json()["status"] == "rejected"
        assert "pending" in resp.json()["reason"].lower()


class TestListPending:
    async def test_list_pending_actions(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        card_id = _get_deck_cards(resp.json())[0]

        await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "move_card",
                "card_ids": [card_id],
                "source_zone_id": "deck",
                "target_zone_id": "center",
            },
            headers=auth_header(tokens[0]),
        )

        resp = await client.get(
            f"/api/tables/{table_id}/actions/pending",
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["proposer_seat_id"] == "seat_0"
