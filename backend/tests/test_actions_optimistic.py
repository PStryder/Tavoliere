import pytest
from httpx import AsyncClient

from backend.tests.conftest import auth_header


async def _setup_table_with_players(client: AsyncClient, tokens: list[str]):
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


class TestSetPhase:
    async def test_set_phase_commits_immediately(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={"action_type": "set_phase", "phase_label": "bidding"},
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "committed"

        # Verify phase changed
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        assert resp.json()["phase"] == "bidding"

    async def test_set_phase_when_locked_fails(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        # Lock phase (host only)
        await client.patch(
            f"/api/tables/{table_id}/settings",
            json={"phase_locked": True},
            headers=auth_header(tokens[0]),
        )

        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={"action_type": "set_phase", "phase_label": "play"},
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 400
        assert "locked" in resp.json()["detail"].lower()


class TestAutoAckPromotion:
    async def test_consensus_promoted_to_optimistic_with_auto_ack(
        self, client: AsyncClient, bootstrapped
    ):
        """When all seats have AUTO_ACK for move_card, it commits immediately."""
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        # Set AUTO_ACK for move_card on all seats
        for i, token in enumerate(tokens):
            resp = await client.patch(
                f"/api/tables/{table_id}/seats/seat_{i}/ack_posture",
                json={"move_card": True, "deal": False, "set_phase": False,
                      "create_zone": False, "undo": False},
                headers=auth_header(token),
            )
            assert resp.status_code == 200

        # Now move_card should commit immediately (optimistic)
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        deck_cards = []
        for z in resp.json()["zones"]:
            if z["zone_id"] == "deck":
                deck_cards = z["card_ids"]
                break
        card_id = deck_cards[0]

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
        assert resp.json()["status"] == "committed"

        # Card should already be in center
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        for z in resp.json()["zones"]:
            if z["zone_id"] == "center":
                assert card_id in z["card_ids"]
                break

    async def test_without_auto_ack_stays_consensus(
        self, client: AsyncClient, bootstrapped
    ):
        """Without AUTO_ACK, move_card is consensus (pending)."""
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        deck_cards = []
        for z in resp.json()["zones"]:
            if z["zone_id"] == "deck":
                deck_cards = z["card_ids"]
                break

        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={
                "action_type": "move_card",
                "card_ids": [deck_cards[0]],
                "source_zone_id": "deck",
                "target_zone_id": "center",
            },
            headers=auth_header(tokens[0]),
        )
        assert resp.json()["status"] == "pending"


class TestDisputeOptimistic:
    async def test_dispute_within_window_rolls_back(
        self, client: AsyncClient, bootstrapped
    ):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        # Set phase (optimistic)
        resp = await client.post(
            f"/api/tables/{table_id}/actions",
            json={"action_type": "set_phase", "phase_label": "wrong_phase"},
            headers=auth_header(tokens[0]),
        )
        action_id = resp.json()["action_id"]

        # Dispute within window
        resp = await client.post(
            f"/api/tables/{table_id}/actions/{action_id}/dispute",
            json={"reason": "other", "reason_text": "Wrong phase"},
            headers=auth_header(tokens[1]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rolled_back"

        # Phase should be rolled back
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        assert resp.json()["phase"] == ""  # back to default
        assert resp.json()["dispute_active"] is True


class TestAckPosture:
    async def test_update_ack_posture(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        resp = await client.patch(
            f"/api/tables/{table_id}/seats/seat_0/ack_posture",
            json={"move_card": True, "deal": True, "set_phase": False,
                  "create_zone": False, "undo": False},
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 200
        assert resp.json()["move_card"] is True
        assert resp.json()["deal"] is True

    async def test_cannot_update_other_seat_posture(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        resp = await client.patch(
            f"/api/tables/{table_id}/seats/seat_1/ack_posture",
            json={"move_card": True, "deal": False, "set_phase": False,
                  "create_zone": False, "undo": False},
            headers=auth_header(tokens[0]),
        )
        assert resp.status_code == 403
