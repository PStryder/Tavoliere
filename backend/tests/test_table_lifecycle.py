import pytest
from httpx import AsyncClient

from backend.tests.conftest import auth_header


def find_zone(zones: list[dict], zone_id: str) -> dict:
    """Find a zone by ID without using next() in async context."""
    for z in zones:
        if z["zone_id"] == zone_id:
            return z
    raise ValueError(f"Zone {zone_id} not found")


class TestTableCreation:
    async def test_create_table(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        resp = await client.post(
            "/api/tables",
            json={"display_name": "Test Table", "deck_recipe": "euchre_24"},
            headers=auth_header(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["display_name"] == "Test Table"
        assert data["deck_recipe"] == "euchre_24"
        assert len(data["cards"]) == 24  # Euchre deck

    async def test_create_standard_52(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        resp = await client.post(
            "/api/tables",
            json={"display_name": "Standard", "deck_recipe": "standard_52"},
            headers=auth_header(token),
        )
        assert resp.status_code == 201
        assert len(resp.json()["cards"]) == 52

    async def test_create_double_pinochle(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        resp = await client.post(
            "/api/tables",
            json={"display_name": "Pinochle", "deck_recipe": "double_pinochle_80"},
            headers=auth_header(token),
        )
        assert resp.status_code == 201
        assert len(resp.json()["cards"]) == 80

    async def test_default_zones_created(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        resp = await client.post(
            "/api/tables",
            json={"display_name": "T", "deck_recipe": "euchre_24"},
            headers=auth_header(token),
        )
        zones = resp.json()["zones"]
        zone_ids = [z["zone_id"] for z in zones]
        assert "deck" in zone_ids
        assert "discard" in zone_ids
        assert "center" in zone_ids

    async def test_deck_zone_has_all_cards(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        resp = await client.post(
            "/api/tables",
            json={"display_name": "T", "deck_recipe": "euchre_24"},
            headers=auth_header(token),
        )
        data = resp.json()
        deck_zone = next(z for z in data["zones"] if z["zone_id"] == "deck")
        assert len(deck_zone["card_ids"]) == 24

    async def test_list_tables(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        await client.post(
            "/api/tables",
            json={"display_name": "T1", "deck_recipe": "euchre_24"},
            headers=auth_header(token),
        )
        resp = await client.get("/api/tables", headers=auth_header(token))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestJoinLeave:
    async def _create_table(self, client, token):
        resp = await client.post(
            "/api/tables",
            json={"display_name": "T", "deck_recipe": "euchre_24"},
            headers=auth_header(token),
        )
        return resp.json()["table_id"]

    async def test_join_table(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        table_id = await self._create_table(client, token)

        resp = await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "North"},
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        seat = resp.json()
        assert seat["display_name"] == "North"
        assert seat["seat_id"] == "seat_0"
        assert seat["player_kind"] == "ai"

    async def test_join_creates_per_seat_zones(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        table_id = await self._create_table(client, token)

        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "North"},
            headers=auth_header(token),
        )

        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(token))
        zones = resp.json()["zones"]
        zone_ids = [z["zone_id"] for z in zones]
        assert "hand_seat_0" in zone_ids
        assert "meld_seat_0" in zone_ids
        assert "tricks_seat_0" in zone_ids

    async def test_first_joiner_is_host(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        table_id = await self._create_table(client, token)

        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "North"},
            headers=auth_header(token),
        )

        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(token))
        assert resp.json()["host_seat_id"] == "seat_0"

    async def test_four_players_join(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await self._create_table(client, tokens[0])

        names = ["North", "East", "South", "West"]
        for i, token in enumerate(tokens):
            resp = await client.post(
                f"/api/tables/{table_id}/join",
                json={"display_name": names[i]},
                headers=auth_header(token),
            )
            assert resp.status_code == 200
            assert resp.json()["seat_id"] == f"seat_{i}"

    async def test_table_full_rejects_fifth(self, client: AsyncClient, bootstrapped):
        tokens = bootstrapped["tokens"]
        table_id = await self._create_table(client, tokens[0])

        for i, token in enumerate(tokens):
            await client.post(
                f"/api/tables/{table_id}/join",
                json={"display_name": f"P{i}"},
                headers=auth_header(token),
            )

        # Create a 5th credential
        bootstrap2 = await client.post("/dev/bootstrap", json={"num_credentials": 1})
        cred5 = bootstrap2.json()["credentials"][0]
        token_resp = await client.post("/api/token", json={
            "client_id": cred5["client_id"],
            "client_secret": cred5["client_secret"],
        })
        token5 = token_resp.json()["access_token"]

        resp = await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "Fifth"},
            headers=auth_header(token5),
        )
        assert resp.status_code == 409

    async def test_rejoin_returns_same_seat(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        table_id = await self._create_table(client, token)

        resp1 = await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "North"},
            headers=auth_header(token),
        )
        resp2 = await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "North"},
            headers=auth_header(token),
        )
        assert resp1.json()["seat_id"] == resp2.json()["seat_id"]

    async def test_leave_table(self, client: AsyncClient, bootstrapped):
        token = bootstrapped["tokens"][0]
        table_id = await self._create_table(client, token)

        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "North"},
            headers=auth_header(token),
        )

        resp = await client.post(
            f"/api/tables/{table_id}/leave",
            headers=auth_header(token),
        )
        assert resp.status_code == 204


class TestVisibility:
    async def _setup_two_players(self, client, tokens):
        resp = await client.post(
            "/api/tables",
            json={"display_name": "T", "deck_recipe": "euchre_24", "max_seats": 4},
            headers=auth_header(tokens[0]),
        )
        table_id = resp.json()["table_id"]

        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "North"},
            headers=auth_header(tokens[0]),
        )
        await client.post(
            f"/api/tables/{table_id}/join",
            json={"display_name": "East"},
            headers=auth_header(tokens[1]),
        )
        return table_id

    async def test_own_hand_visible(self, client: AsyncClient, bootstrapped):
        """A player can see their own hand zone contents."""
        tokens = bootstrapped["tokens"]
        table_id = await self._setup_two_players(client, tokens)

        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        zones = resp.json()["zones"]
        hand_0 = find_zone(zones, "hand_seat_0")
        # Hand zone should have card_ids field (even if empty)
        assert "card_ids" in hand_0

    async def test_other_hand_hidden(self, client: AsyncClient, bootstrapped):
        """A player cannot see another player's hand zone card_ids."""
        tokens = bootstrapped["tokens"]
        table_id = await self._setup_two_players(client, tokens)

        # Player 0 should not see player 1's hand contents
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        zones = resp.json()["zones"]
        hand_1 = find_zone(zones, "hand_seat_1")
        assert hand_1["card_ids"] == []
        assert "card_count" in hand_1

    async def test_public_zones_visible_to_all(self, client: AsyncClient, bootstrapped):
        """All players see public zone contents."""
        tokens = bootstrapped["tokens"]
        table_id = await self._setup_two_players(client, tokens)

        for token in tokens[:2]:
            resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(token))
            zones = resp.json()["zones"]
            deck = find_zone(zones, "deck")
            assert len(deck["card_ids"]) == 24

    async def test_seat_public_zones_visible_to_all(self, client: AsyncClient, bootstrapped):
        """Meld and tricks zones are visible to all players."""
        tokens = bootstrapped["tokens"]
        table_id = await self._setup_two_players(client, tokens)

        # Player 0 can see player 1's meld zone
        resp = await client.get(f"/api/tables/{table_id}", headers=auth_header(tokens[0]))
        zones = resp.json()["zones"]
        meld_1 = find_zone(zones, "meld_seat_1")
        assert "card_ids" in meld_1  # visible, just empty
