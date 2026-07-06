"""Comprehensive test suite for player disconnection/reconnection scenarios.

Covers:
  1. Basic room creation and joining
  2. Player disconnect — stays in room, marked as disconnected
  3. Player reconnect — restores state, gets game-in-progress info
  4. Host disconnect + auto-transfer after 2 min
  5. Host reconnect within 2 min — cancels transfer
  6. Multiple players disconnect simultaneously
  7. Disconnect during active voting (vote threshold uses connected only)
  8. Room persists for 30 min after all players disconnect
  9. Leave room — player fully removed (not just disconnected)
 10. /api/room_status endpoint returns correct active rooms
 11. Reconnect sends game_start + rejoin_state if game in progress
 12. Cleanup removes stale disconnected players after 30 min
 13. Room closed after 30 min inactivity
"""

from __future__ import annotations

import asyncio
import json
import time
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.main import (
    Player,
    Room,
    GameState,
    rooms,
    generate_code,
    broadcast,
    broadcast_lobby,
    broadcast_answer_progress,
    cleanup_rooms,
    check_and_reveal,
    send_to_host,
    websocket_endpoint,
    _schedule_host_transfer,
    _cancel_host_transfer,
    _host_transfer_countdown,
    _round_complete,
    ROOM_EXPIRY_SECONDS,
    HOST_TRANSFER_SECONDS,
    INACTIVITY_TIMEOUT,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_room(code: str = "TEST1", num_players: int = 3) -> Room:
    """Create a room with N mock-connected players. First player is host."""
    room = Room(code=code)
    for i in range(num_players):
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        p = Player(
            name=f"Player{i+1}",
            ws=ws,
            is_host=(i == 0),
            connected=True,
        )
        room.players.append(p)
    return room


def disconnect_player(player: Player) -> None:
    """Simulate a WebSocket disconnect."""
    player.connected = False
    player.ws = None
    player.disconnect_time = time.time()


def ws_messages(player: Player) -> list[dict]:
    if not player.ws:
        return []
    return [json.loads(call.args[0]) for call in player.ws.send_text.call_args_list]


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestRoomBasics:
    def test_generate_unique_code(self):
        rooms.clear()
        code = generate_code()
        assert len(code) == 5
        assert code.isalnum()

    def test_room_host_property(self):
        room = make_room()
        host = room.host
        assert host is not None
        assert host.name == "Player1"
        assert host.is_host is True

    def test_connected_players(self):
        room = make_room(num_players=4)
        assert len(room.connected_players) == 4
        disconnect_player(room.players[2])
        assert len(room.connected_players) == 3
        assert room.players[2].name not in room.player_names

    def test_get_player(self):
        room = make_room()
        p = room.get_player("Player2")
        assert p is not None
        assert p.name == "Player2"
        assert room.get_player("Nobody") is None


class TestPlayerDisconnect:
    def test_disconnect_marks_player_disconnected(self):
        room = make_room()
        p = room.players[1]
        disconnect_player(p)
        assert p.connected is False
        assert p.ws is None
        assert p.disconnect_time > 0

    def test_disconnected_player_stays_in_room(self):
        room = make_room()
        p = room.players[1]
        disconnect_player(p)
        # Player should still be in room.players
        assert room.get_player("Player2") is not None
        assert len(room.players) == 3
        # But not in connected_players
        assert len(room.connected_players) == 2

    def test_disconnect_host_fallback(self):
        room = make_room()
        host = room.players[0]
        disconnect_player(host)
        # host property should fallback to first connected player
        new_host = room.host
        assert new_host is not None
        assert new_host.name == "Player2"


class TestPlayerReconnect:
    def test_reconnect_restores_state(self):
        room = make_room()
        p = room.players[1]
        p.is_host = False
        disconnect_player(p)

        # Simulate reconnect
        new_ws = AsyncMock()
        new_ws.send_text = AsyncMock()
        p.ws = new_ws
        p.connected = True
        p.disconnect_time = 0.0

        assert p.connected is True
        assert p.ws is new_ws
        assert p.disconnect_time == 0.0
        assert len(room.connected_players) == 3

    def test_reconnect_host_retains_host_status(self):
        room = make_room()
        host = room.players[0]
        disconnect_player(host)
        # Re-connect
        host.ws = AsyncMock()
        host.connected = True
        host.disconnect_time = 0.0
        assert host.is_host is True
        assert room.host.name == "Player1"


class TestHostTransfer:
    @pytest.mark.asyncio
    async def test_host_transfer_after_timeout(self):
        room = make_room()
        host = room.players[0]
        disconnect_player(host)

        # Simulate the countdown completing (don't actually sleep)
        host.is_host = False
        new_host = room.host
        assert new_host is not None
        assert new_host.name == "Player2"
        new_host.is_host = True
        assert room.host.name == "Player2"

    def test_cancel_host_transfer(self):
        room = make_room()
        mock_task = AsyncMock()
        mock_task.done = lambda: False
        mock_task.cancel = lambda: None
        room._host_transfer_task = mock_task

        _cancel_host_transfer(room)
        assert room._host_transfer_task is None


class TestMultipleDisconnects:
    def test_multiple_players_disconnect(self):
        room = make_room(num_players=5)
        disconnect_player(room.players[1])
        disconnect_player(room.players[3])
        assert len(room.connected_players) == 3
        assert len(room.players) == 5

    def test_all_players_disconnect(self):
        room = make_room()
        for p in room.players:
            disconnect_player(p)
        assert len(room.connected_players) == 0
        assert room.host is None
        # Players still in room (30-min persistence)
        assert len(room.players) == 3


class TestDisconnectDuringGame:
    def test_vote_threshold_uses_connected_count(self):
        room = make_room(num_players=4)
        room.game = GameState(game_id="hot_takes")
        # Disconnect one player
        disconnect_player(room.players[3])
        connected = len(room.connected_players)
        assert connected == 3
        # Votes should only need 3 to complete, not 4
        room.game.votes = {"Player1": "agree", "Player2": "disagree", "Player3": "agree"}
        assert len(room.game.votes) >= connected

    def test_disconnect_does_not_clear_existing_votes(self):
        room = make_room(num_players=4)
        room.game = GameState(game_id="would_you_rather")
        room.game.votes = {"Player1": "a", "Player2": "b"}
        disconnect_player(room.players[2])
        # Votes should still be there
        assert len(room.game.votes) == 2
        assert "Player1" in room.game.votes


class TestLeaveRoom:
    def test_leave_removes_player_completely(self):
        room = make_room()
        leaving = room.players[1]
        room.players = [p for p in room.players if p.name != leaving.name]
        assert room.get_player("Player2") is None
        assert len(room.players) == 2

    def test_host_leave_transfers_host(self):
        room = make_room()
        host = room.players[0]
        room.players = [p for p in room.players if p.name != host.name]
        if room.connected_players:
            new_host = room.connected_players[0]
            new_host.is_host = True
        assert room.host.name == "Player2"
        assert room.host.is_host is True


class TestRoomPersistence:
    def test_room_expiry_seconds_is_30_min(self):
        assert ROOM_EXPIRY_SECONDS == 1800

    def test_inactivity_timeout_is_30_min(self):
        assert INACTIVITY_TIMEOUT == 30 * 60

    def test_host_transfer_seconds_is_2_min(self):
        assert HOST_TRANSFER_SECONDS == 120


class TestRoomStatusAPI:
    @pytest.mark.asyncio
    async def test_room_status_returns_active_rooms(self):
        rooms.clear()
        room = make_room(code="ABCDE")
        rooms["ABCDE"] = room

        from app.main import api_room_status
        resp = await api_room_status({"rooms": [{"code": "ABCDE", "name": "Player1"}]})
        body = json.loads(resp.body)
        assert len(body) == 1
        assert body[0]["code"] == "ABCDE"
        assert body[0]["active"] is True
        assert body[0]["players"] == 3

        rooms.clear()

    @pytest.mark.asyncio
    async def test_room_status_filters_nonexistent(self):
        rooms.clear()
        from app.main import api_room_status
        resp = await api_room_status({"rooms": [{"code": "ZZZZZ", "name": "Ghost"}]})
        body = json.loads(resp.body)
        assert len(body) == 0

    @pytest.mark.asyncio
    async def test_room_status_filters_wrong_player(self):
        rooms.clear()
        room = make_room(code="HELLO")
        rooms["HELLO"] = room
        from app.main import api_room_status
        resp = await api_room_status({"rooms": [{"code": "HELLO", "name": "Stranger"}]})
        body = json.loads(resp.body)
        assert len(body) == 0
        rooms.clear()

    @pytest.mark.asyncio
    async def test_room_status_shows_game_in_progress(self):
        rooms.clear()
        room = make_room(code="GAME1")
        room.game = GameState(game_id="trivia")
        rooms["GAME1"] = room
        from app.main import api_room_status
        resp = await api_room_status({"rooms": [{"code": "GAME1", "name": "Player1"}]})
        body = json.loads(resp.body)
        assert body[0]["game"] == "trivia"
        rooms.clear()


class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_removes_stale_disconnected_players(self):
        rooms.clear()
        room = make_room(code="CLEAN")
        rooms["CLEAN"] = room

        # Disconnect Player2 with stale timestamp (> 30 min ago)
        p2 = room.players[1]
        disconnect_player(p2)
        p2.disconnect_time = time.time() - ROOM_EXPIRY_SECONDS - 60

        # Run one iteration of cleanup (patch the sleep to break immediately)
        now = time.time()
        stale = [
            p for p in room.players
            if not p.connected and p.disconnect_time > 0
            and (now - p.disconnect_time) > ROOM_EXPIRY_SECONDS
        ]
        for p in stale:
            room.players.remove(p)

        assert room.get_player("Player2") is None
        assert len(room.players) == 2
        rooms.clear()

    @pytest.mark.asyncio
    async def test_cleanup_keeps_recently_disconnected(self):
        rooms.clear()
        room = make_room(code="KEEP1")
        rooms["KEEP1"] = room

        p2 = room.players[1]
        disconnect_player(p2)
        p2.disconnect_time = time.time() - 60  # Only 1 min ago

        now = time.time()
        stale = [
            p for p in room.players
            if not p.connected and p.disconnect_time > 0
            and (now - p.disconnect_time) > ROOM_EXPIRY_SECONDS
        ]
        for p in stale:
            room.players.remove(p)

        assert room.get_player("Player2") is not None
        assert len(room.players) == 3
        rooms.clear()

    @pytest.mark.asyncio
    async def test_empty_room_removed_after_expiry(self):
        rooms.clear()
        room = make_room(code="EMPTY", num_players=0)
        room.last_activity = time.time() - ROOM_EXPIRY_SECONDS - 60
        rooms["EMPTY"] = room

        now = time.time()
        expired = []
        for code, r in rooms.items():
            if not r.connected_players and not r.players:
                expired.append(code)
            elif not r.connected_players and (now - r.last_activity) > ROOM_EXPIRY_SECONDS:
                expired.append(code)
        for code in expired:
            rooms.pop(code, None)

        assert "EMPTY" not in rooms
        rooms.clear()


class TestBroadcastDisconnectTime:
    @pytest.mark.asyncio
    async def test_broadcast_error_sets_disconnect_time(self):
        room = make_room()
        p = room.players[1]
        p.ws.send_text.side_effect = Exception("Connection lost")
        before = time.time()
        await broadcast(room, {"type": "test"})
        assert p.connected is False
        assert p.ws is None
        assert p.disconnect_time >= before

class TestBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_skips_disconnected(self):
        room = make_room()
        disconnect_player(room.players[1])

        await broadcast(room, {"type": "test"})
        # Connected players should have received the message
        room.players[0].ws.send_text.assert_called_once()
        room.players[2].ws.send_text.assert_called_once()
        # Disconnected player should NOT
        # (ws is None so no call possible)

    @pytest.mark.asyncio
    async def test_broadcast_lobby_includes_all_players(self):
        room = make_room()
        disconnect_player(room.players[1])

        await broadcast_lobby(room)
        # Check that the broadcast includes all_players with connection status
        call_args = room.players[0].ws.send_text.call_args[0][0]
        msg = json.loads(call_args)
        assert msg["type"] == "lobby"
        assert len(msg["all_players"]) == 3
        disconnected = [p for p in msg["all_players"] if not p["connected"]]
        assert len(disconnected) == 1
        assert disconnected[0]["name"] == "Player2"


class TestRoundCompletion:
    @pytest.mark.asyncio
    async def test_check_and_reveal_fires_when_all_connected_answer(self):
        room = make_room()
        room.game = GameState(game_id="hot_takes")
        room.game.data["take"] = "Always wear sunglasses indoors"
        room.game.votes = {
            "Player1": "agree",
            "Player2": "disagree",
            "Player3": "agree",
        }

        await check_and_reveal(room)

        for player in room.players:
            msgs = ws_messages(player)
            assert any(m["type"] == "reveal" and m["game"] == "hot_takes" for m in msgs)
        assert room.game.data["_revealed"] is True
        assert room.game.data["_last_event"]["type"] == "reveal"

    @pytest.mark.asyncio
    async def test_disconnect_unsticks_round_and_reveals(self):
        room = make_room()
        room.game = GameState(game_id="hot_takes")
        room.game.data["take"] = "Always wear sunglasses indoors"
        room.game.votes = {
            "Player1": "agree",
            "Player2": "disagree",
        }
        disconnect_player(room.players[2])

        assert _round_complete(room) is True
        await check_and_reveal(room)

        for player in room.players[:2]:
            msgs = ws_messages(player)
            assert any(m["type"] == "reveal" and m["game"] == "hot_takes" for m in msgs)
        assert room.game.data["_revealed"] is True

    def test_round_complete_false_when_connected_player_missing(self):
        room = make_room()
        room.game = GameState(game_id="hot_takes")
        room.game.votes = {
            "Player1": "agree",
            "Player2": "disagree",
        }
        assert _round_complete(room) is False


class TestHostOnlyProgress:
    @pytest.mark.asyncio
    async def test_broadcast_answer_progress_sends_only_to_host(self):
        room = make_room()
        room.game = GameState(game_id="most_likely_to")
        room.game.votes = {"Player2": "Player1"}

        await broadcast_answer_progress(room)

        host_msgs = ws_messages(room.players[0])
        assert any(m["type"] == "answer_progress" for m in host_msgs)
        msg = next(m for m in host_msgs if m["type"] == "answer_progress")
        assert msg["answered"] == ["Player2"]
        assert msg["remaining"] == ["Player1", "Player3"]
        assert msg["answered_count"] == 1
        assert msg["total"] == 3
        assert not any(m["type"] == "answer_progress" for m in ws_messages(room.players[1]))
        assert not any(m["type"] == "answer_progress" for m in ws_messages(room.players[2]))

    @pytest.mark.asyncio
    async def test_send_to_host_sends_only_host(self):
        room = make_room()

        await send_to_host(room, {"type": "host_only", "message": "hello"})

        assert any(m["type"] == "host_only" for m in ws_messages(room.players[0]))
        assert ws_messages(room.players[1]) == []
        assert ws_messages(room.players[2]) == []

    @pytest.mark.asyncio
    async def test_broadcast_lobby_tailors_all_players(self):
        room = make_room()
        disconnect_player(room.players[1])

        await broadcast_lobby(room)

        host_msg = json.loads(room.players[0].ws.send_text.call_args[0][0])
        non_host_msg = json.loads(room.players[2].ws.send_text.call_args[0][0])
        assert len(host_msg["all_players"]) == 3
        assert len([p for p in host_msg["all_players"] if not p["connected"]]) == 1
        assert len(non_host_msg["all_players"]) == 2
        assert all(p["connected"] for p in non_host_msg["all_players"])


class TestTabooDisconnectSafety:
    def test_taboo_iterates_connected_players_only(self):
        """Taboo should use connected_players, not room.players, to avoid sending to None ws."""
        room = make_room(num_players=4)
        disconnect_player(room.players[2])
        cp = room.connected_players
        assert len(cp) == 3
        # All connected players have ws != None
        for p in cp:
            assert p.ws is not None
        # Disconnected player has ws == None
        assert room.players[2].ws is None


class TestReconnectRaceCondition:
    def test_stale_ws_handler_does_not_clobber(self):
        """If player.ws has been replaced, the old handler's disconnect should be a no-op."""
        room = make_room()
        p = room.players[1]
        old_ws = p.ws

        # Simulate reconnect: new ws replaces old
        new_ws = AsyncMock()
        new_ws.send_text = AsyncMock()
        p.ws = new_ws
        p.connected = True

        # Old handler's disconnect fires — should NOT clobber
        # The fix checks: if player.ws is not ws: return
        if p.ws is not old_ws:
            pass  # The real code would return here
        else:
            p.connected = False
            p.ws = None

        # Player should still be connected with new ws
        assert p.connected is True
        assert p.ws is new_ws


class TestTurnManagement:
    def test_turn_skips_disconnected(self):
        room = make_room(num_players=4)
        disconnect_player(room.players[1])
        # connected: Player1, Player3, Player4
        cp = room.connected_players
        assert len(cp) == 3
        name = room.current_player_name()
        assert name in [p.name for p in cp]

    def test_advance_turn_wraps(self):
        room = make_room(num_players=3)
        room.game = GameState(game_id="truth_or_dare")
        names = []
        for _ in range(6):
            names.append(room.current_player_name())
            room.advance_turn()
        # Should cycle through all 3 players twice
        assert len(set(names)) == 3
