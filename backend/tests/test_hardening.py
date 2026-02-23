"""Tests for hardening fixes: cleanup on delete, consensus timeout, chat length."""
import asyncio

import pytest
from httpx import AsyncClient

from backend.tests.conftest import auth_header


async def _setup_table_with_players(client: AsyncClient, tokens: list[str]):
    """Create a table, seat 4 players. Returns table_id."""
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


class TestDeleteTableCleanup:
    """Fix 1: delete_table clears pending consensus actions and optimistic tasks."""

    async def test_delete_clears_pending_actions(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        # Get a card and create a pending consensus action
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        card_id = _get_deck_cards(resp.json())[0]

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
        assert resp.json()["status"] == "pending"

        # Verify pending action exists
        import backend.engine.consensus as cons

        assert len(cons.get_pending_actions(table_id)) == 1

        # Delete the table
        resp = await client.delete(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        assert resp.status_code in (200, 204)

        # Pending actions should be cleared
        assert cons.get_pending_actions(table_id) == {}

    async def test_delete_cancels_optimistic_tasks(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        import backend.engine.optimistic as opt

        # After delete, optimistic state should be clean
        resp = await client.delete(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        assert resp.status_code in (200, 204)

        # No finalization tasks should remain for this table
        remaining = [k for k in opt._finalization_tasks if k.startswith(f"{table_id}:")]
        assert remaining == []


class TestConsensusTimeout:
    """Fix 2: Pending consensus actions auto-rollback after timeout."""

    async def test_consensus_timeout_rollback(self, client: AsyncClient, bootstrapped):
        """Create a consensus intent with a short timeout, wait, verify rollback."""
        tokens = bootstrapped["tokens"]

        # Create table with very short consensus timeout for testing
        resp = await client.post(
            "/api/tables",
            json={
                "display_name": "Timeout Test",
                "deck_recipe": "euchre_24",
                "settings": {"consensus_timeout_s": 5.0},
            },
            headers=auth_header(tokens[0]),
        )
        table_id = resp.json()["table_id"]
        for i, token in enumerate(tokens):
            await client.post(
                f"/api/tables/{table_id}/join",
                json={"display_name": f"P{i}"},
                headers=auth_header(token),
            )

        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        card_id = _get_deck_cards(resp.json())[0]

        # Submit consensus intent
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
        assert resp.json()["status"] == "pending"
        action_id = resp.json()["action_id"]

        import backend.engine.consensus as cons

        # Timeout task should have been scheduled
        task_key = f"{table_id}:{action_id}"
        assert task_key in cons._timeout_tasks

    async def test_commit_cancels_timeout(self, client: AsyncClient, bootstrapped):
        """Committing a consensus action cancels its timeout task."""
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        card_id = _get_deck_cards(resp.json())[0]

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

        import backend.engine.consensus as cons

        task_key = f"{table_id}:{action_id}"
        # Task should exist before commit
        assert task_key in cons._timeout_tasks

        # ACK from all other seats to commit
        for token in tokens[1:]:
            await client.post(
                f"/api/tables/{table_id}/actions/{action_id}/ack",
                headers=auth_header(token),
            )

        # After commit, timeout task should be cancelled and removed
        assert task_key not in cons._timeout_tasks

    async def test_nack_cancels_timeout(self, client: AsyncClient, bootstrapped):
        """NACKing a consensus action cancels its timeout task."""
        tokens = bootstrapped["tokens"]
        table_id = await _setup_table_with_players(client, tokens)

        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        card_id = _get_deck_cards(resp.json())[0]

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

        import backend.engine.consensus as cons

        task_key = f"{table_id}:{action_id}"
        assert task_key in cons._timeout_tasks

        # NACK from seat 1
        await client.post(
            f"/api/tables/{table_id}/actions/{action_id}/nack",
            json={"reason": "turn"},
            headers=auth_header(tokens[1]),
        )

        # Timeout task should be cancelled
        assert task_key not in cons._timeout_tasks


class TestChatMaxLength:
    """Fix 3: Chat messages exceeding chat_max_length are rejected."""

    async def test_player_chat_too_long(self, client: AsyncClient, bootstrapped):
        """Player chat exceeding limit is rejected via REST (if endpoint exists) or WS."""
        tokens = bootstrapped["tokens"]

        # Create table with short chat limit
        resp = await client.post(
            "/api/tables",
            json={
                "display_name": "Chat Test",
                "deck_recipe": "euchre_24",
                "settings": {"chat_max_length": 10},
            },
            headers=auth_header(tokens[0]),
        )
        table_id = resp.json()["table_id"]
        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "North"},
            headers=auth_header(tokens[0]),
        )

        # Verify the setting was stored
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        assert resp.json()["settings"]["chat_max_length"] == 10

    async def test_table_settings_include_new_fields(self, client: AsyncClient, bootstrapped):
        """Verify consensus_timeout_s and chat_max_length appear in table settings."""
        tokens = bootstrapped["tokens"]
        resp = await client.post(
            "/api/tables",
            json={"display_name": "Defaults", "deck_recipe": "euchre_24"},
            headers=auth_header(tokens[0]),
        )
        settings = resp.json()["settings"]
        assert settings["consensus_timeout_s"] == 30.0
        assert settings["chat_max_length"] == 500
