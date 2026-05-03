"""Drunk Games Night — FastAPI backend with WebSocket rooms."""

from __future__ import annotations

import asyncio
import json
import random
import string
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.game_data import KINGS_CUP_RULES, SUITS, SUIT_SYMBOLS, ShuffledDeck
from app.database import (
    init_db, seed_from_game_data, get_content,
    add_content, replace_content, delete_content, count_content,
)

app = FastAPI(title="Drunk Games Night")

STATIC_DIR = Path(__file__).parent / "static"

# ─── Data Structures ─────────────────────────────────────────────────────────

ROOM_EXPIRY_SECONDS = 300       # 5 min grace period for empty rooms
HOST_TRANSFER_SECONDS = 120     # 2 min before host is transferred
INACTIVITY_TIMEOUT = 30 * 60    # 30 min inactivity timeout

@dataclass
class Player:
    name: str
    ws: WebSocket | None = None
    is_host: bool = False
    connected: bool = True

@dataclass
class GameState:
    game_id: str = ""
    current_player_idx: int = 0
    round_num: int = 0
    data: dict[str, Any] = field(default_factory=dict)
    votes: dict[str, str] = field(default_factory=dict)
    answers: dict[str, str] = field(default_factory=dict)
    timer_end: float = 0.0

@dataclass
class Room:
    code: str
    players: list[Player] = field(default_factory=list)
    game: GameState = field(default_factory=GameState)
    decks: dict[str, ShuffledDeck] = field(default_factory=dict)
    kings_drawn: int = 0
    spicy_mode: bool = False
    last_activity: float = field(default_factory=time.time)
    _host_transfer_task: asyncio.Task | None = field(default=None, repr=False)

    @property
    def host(self) -> Player | None:
        for p in self.players:
            if p.is_host and p.connected:
                return p
        # fallback: first connected player
        for p in self.players:
            if p.connected:
                return p
        return None

    @property
    def connected_players(self) -> list[Player]:
        return [p for p in self.players if p.connected]

    @property
    def player_names(self) -> list[str]:
        return [p.name for p in self.players if p.connected]

    def get_player(self, name: str) -> Player | None:
        for p in self.players:
            if p.name == name:
                return p
        return None

    def current_player_name(self) -> str:
        cp = self.connected_players
        if not cp:
            return ""
        idx = self.game.current_player_idx % len(cp)
        return cp[idx].name

    def advance_turn(self) -> str:
        cp = self.connected_players
        if cp:
            self.game.current_player_idx = (self.game.current_player_idx + 1) % len(cp)
        self.game.round_num += 1
        return self.current_player_name()

    def ensure_deck(self, key: str, items: list) -> ShuffledDeck:
        if key not in self.decks:
            self.decks[key] = ShuffledDeck(items)
        return self.decks[key]


# ─── Room Registry ───────────────────────────────────────────────────────────

rooms: dict[str, Room] = {}

def generate_code() -> str:
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if code not in rooms:
            return code


# ─── Broadcast Helpers ───────────────────────────────────────────────────────

async def broadcast(room: Room, msg: dict) -> None:
    payload = json.dumps(msg)
    for p in room.players:
        if p.connected and p.ws:
            try:
                await p.ws.send_text(payload)
            except Exception:
                p.connected = False
                p.ws = None

async def send(ws: WebSocket, msg: dict) -> None:
    await ws.send_text(json.dumps(msg))

async def broadcast_lobby(room: Room) -> None:
    await broadcast(room, {
        "type": "lobby",
        "players": room.player_names,
        "host": room.host.name if room.host else "",
        "room_code": room.code,
        "spicy_mode": room.spicy_mode,
    })


# ─── Game Logic ──────────────────────────────────────────────────────────────

GAME_CATALOG = [
    {"id": "truth_or_dare",    "name": "Truth or Dare",       "emoji": "🤫", "desc": "Spill secrets or face the dare", "min_players": 2},
    {"id": "never_have_i_ever","name": "Never Have I Ever",   "emoji": "🙈", "desc": "Drink if you have done it",      "min_players": 2},
    {"id": "would_you_rather", "name": "Would You Rather",    "emoji": "🤔", "desc": "Pick between two wild options",   "min_players": 2},
    {"id": "kings_cup",        "name": "Kings Cup",           "emoji": "👑", "desc": "Draw a card, follow the rule",    "min_players": 2},
    {"id": "most_likely_to",   "name": "Most Likely To",      "emoji": "👉", "desc": "Vote on who fits the scenario",   "min_players": 3},
    {"id": "categories",       "name": "Categories",          "emoji": "📝", "desc": "Name things in a category",       "min_players": 2},
    {"id": "trivia",           "name": "Trivia",              "emoji": "🧠", "desc": "Test your boozy knowledge",       "min_players": 2},
    {"id": "hot_takes",        "name": "Hot Takes",           "emoji": "🔥", "desc": "Agree or disagree — minority drinks", "min_players": 3},
    {"id": "taboo",            "name": "Taboo",               "emoji": "🚫", "desc": "Describe the word, skip the taboos", "min_players": 3},
    {"id": "two_truths",       "name": "Two Truths & a Lie",  "emoji": "🤥", "desc": "Guess which one is the lie",      "min_players": 3},
    {"id": "rhyme_time",       "name": "Rhyme Time",          "emoji": "🎤", "desc": "Keep the rhyme chain going",      "min_players": 2},
    {"id": "word_association", "name": "Word Association",    "emoji": "💬", "desc": "Say the first word you think of",  "min_players": 2},
]

async def start_game(room: Room, game_id: str) -> None:
    room.game = GameState(game_id=game_id)
    room.game.current_player_idx = 0
    room.kings_drawn = 0

    await broadcast(room, {"type": "game_start", "game_id": game_id})
    await send_next_round(room)

def _pick(room: Room, game: str) -> list:
    """Load content from DB. Combines normal+spicy when spicy mode is on."""
    items = get_content(game, "normal")
    if room.spicy_mode:
        items = items + get_content(game, "spicy")
    return items

async def send_next_round(room: Room) -> None:
    g = room.game
    gid = g.game_id
    g.votes = {}
    g.answers = {}
    current = room.current_player_name()
    sp = room.spicy_mode

    if gid == "truth_or_dare":
        await broadcast(room, {
            "type": "round",
            "game": gid,
            "current_player": current,
            "phase": "choose",
            "round": g.round_num,
        })

    elif gid == "never_have_i_ever":
        key = "nhie_s" if sp else "nhie"
        deck = room.ensure_deck(key, _pick(room, "never_have_i_ever"))
        statement = deck.draw()
        await broadcast(room, {
            "type": "round",
            "game": gid,
            "statement": statement,
            "round": g.round_num,
        })

    elif gid == "would_you_rather":
        key = "wyr_s" if sp else "wyr"
        deck = room.ensure_deck(key, _pick(room, "would_you_rather"))
        pair = deck.draw()
        g.data["options"] = list(pair)
        await broadcast(room, {
            "type": "round",
            "game": gid,
            "option_a": pair[0],
            "option_b": pair[1],
            "round": g.round_num,
        })

    elif gid == "kings_cup":
        values = list(KINGS_CUP_RULES.keys())
        card_val = random.choice(values)
        suit = random.choice(SUITS)
        rule_info = KINGS_CUP_RULES[card_val]
        if card_val == "K":
            room.kings_drawn += 1
        await broadcast(room, {
            "type": "round",
            "game": gid,
            "card": card_val,
            "suit": suit,
            "suit_symbol": SUIT_SYMBOLS[suit],
            "rule_name": rule_info["name"],
            "rule": rule_info["rule"],
            "current_player": current,
            "kings_drawn": room.kings_drawn,
            "round": g.round_num,
        })

    elif gid == "most_likely_to":
        key = "mlt_s" if sp else "mlt"
        deck = room.ensure_deck(key, _pick(room, "most_likely_to"))
        scenario = deck.draw()
        g.data["scenario"] = scenario
        await broadcast(room, {
            "type": "round",
            "game": gid,
            "scenario": scenario,
            "players": room.player_names,
            "round": g.round_num,
        })

    elif gid == "categories":
        key = "cat_s" if sp else "cat"
        deck = room.ensure_deck(key, _pick(room, "categories"))
        category = deck.draw()
        g.data["category"] = category
        g.timer_end = time.time() + 30
        await broadcast(room, {
            "type": "round",
            "game": gid,
            "category": category,
            "current_player": current,
            "timer_seconds": 30,
            "round": g.round_num,
        })

    elif gid == "trivia":
        deck = room.ensure_deck("trivia", _pick(room, "trivia"))
        q = deck.draw()
        g.data["answer"] = q["answer"]
        g.data["question"] = q["q"]
        g.data["options"] = q["options"]
        await broadcast(room, {
            "type": "round",
            "game": gid,
            "question": q["q"],
            "options": q["options"],
            "round": g.round_num,
        })

    elif gid == "hot_takes":
        key = "ht_s" if sp else "ht"
        deck = room.ensure_deck(key, _pick(room, "hot_takes"))
        take = deck.draw()
        g.data["take"] = take
        await broadcast(room, {
            "type": "round",
            "game": gid,
            "take": take,
            "round": g.round_num,
        })

    elif gid == "taboo":
        key = "taboo_s" if sp else "taboo"
        deck = room.ensure_deck(key, _pick(room, "taboo"))
        card = deck.draw()
        g.data["word"] = card["word"]
        g.data["forbidden"] = card["forbidden"]
        g.timer_end = time.time() + 60

        for p in room.players:
            if p.name == current:
                await send(p.ws, {
                    "type": "round",
                    "game": gid,
                    "role": "describer",
                    "word": card["word"],
                    "forbidden": card["forbidden"],
                    "current_player": current,
                    "timer_seconds": 60,
                    "round": g.round_num,
                })
            else:
                await send(p.ws, {
                    "type": "round",
                    "game": gid,
                    "role": "guesser",
                    "current_player": current,
                    "timer_seconds": 60,
                    "round": g.round_num,
                })

    elif gid == "two_truths":
        key = "tt_s" if sp else "tt"
        deck = room.ensure_deck(key, _pick(room, "two_truths"))
        prompt = deck.draw()
        await broadcast(room, {
            "type": "round",
            "game": gid,
            "prompt": prompt,
            "current_player": current,
            "round": g.round_num,
        })

    elif gid == "rhyme_time":
        key = "rt_s" if sp else "rt"
        deck = room.ensure_deck(key, _pick(room, "rhyme_starters"))
        word = deck.draw()
        await broadcast(room, {
            "type": "round",
            "game": gid,
            "starter_word": word,
            "current_player": current,
            "round": g.round_num,
        })

    elif gid == "word_association":
        key = "wa_s" if sp else "wa"
        deck = room.ensure_deck(key, _pick(room, "word_association"))
        word = deck.draw()
        await broadcast(room, {
            "type": "round",
            "game": gid,
            "starter_word": word,
            "current_player": current,
            "round": g.round_num,
        })


async def handle_game_action(room: Room, player_name: str, data: dict) -> None:
    g = room.game
    gid = g.game_id
    action = data.get("action", "")

    connected_count = len(room.connected_players)

    if gid == "truth_or_dare" and action == "pick":
        sp = room.spicy_mode
        choice = data.get("choice", "truth")
        if choice == "truth":
            key = "truths_s" if sp else "truths"
            deck = room.ensure_deck(key, _pick(room, "truths"))
            prompt = deck.draw()
        else:
            key = "dares_s" if sp else "dares"
            deck = room.ensure_deck(key, _pick(room, "dares"))
            prompt = deck.draw()
        await broadcast(room, {
            "type": "reveal",
            "game": gid,
            "choice": choice,
            "prompt": prompt,
            "player": player_name,
        })

    elif gid == "never_have_i_ever" and action == "drink":
        drank = data.get("drank", False)
        g.answers[player_name] = "drank" if drank else "safe"
        if len(g.answers) >= connected_count:
            drinkers = [n for n, v in g.answers.items() if v == "drank"]
            await broadcast(room, {
                "type": "reveal",
                "game": gid,
                "drinkers": drinkers,
                "total": len(room.players),
            })

    elif gid == "would_you_rather" and action == "vote":
        choice = data.get("choice", "a")
        g.votes[player_name] = choice
        if len(g.votes) >= connected_count:
            a_voters = [n for n, v in g.votes.items() if v == "a"]
            b_voters = [n for n, v in g.votes.items() if v == "b"]
            tied = len(a_voters) == len(b_voters)
            if tied:
                minority = []
            else:
                minority = a_voters if len(a_voters) < len(b_voters) else b_voters
            await broadcast(room, {
                "type": "reveal",
                "game": gid,
                "a_voters": a_voters,
                "b_voters": b_voters,
                "minority": minority,
                "option_a": g.data.get("options", ["", ""])[0],
                "option_b": g.data.get("options", ["", ""])[1],
            })

    elif gid == "most_likely_to" and action == "vote":
        voted_for = data.get("voted_for", "")
        g.votes[player_name] = voted_for
        await broadcast(room, {
            "type": "vote_update",
            "game": gid,
            "votes_in": len(g.votes),
            "total": connected_count,
        })
        if len(g.votes) >= connected_count:
            tally: dict[str, int] = {}
            for v in g.votes.values():
                tally[v] = tally.get(v, 0) + 1
            max_votes = max(tally.values())
            winners = [n for n, c in tally.items() if c == max_votes]
            await broadcast(room, {
                "type": "reveal",
                "game": gid,
                "tally": tally,
                "winners": winners,
                "scenario": g.data.get("scenario", ""),
            })

    elif gid == "trivia" and action == "answer":
        answer_idx = data.get("answer", -1)
        g.answers[player_name] = str(answer_idx)
        await broadcast(room, {
            "type": "vote_update",
            "game": gid,
            "votes_in": len(g.answers),
            "total": connected_count,
        })
        if len(g.answers) >= connected_count:
            correct = g.data.get("answer", -1)
            results: dict[str, bool] = {}
            choices: dict[str, int] = {}
            for n, a in g.answers.items():
                results[n] = int(a) == correct
                choices[n] = int(a)
            await broadcast(room, {
                "type": "reveal",
                "game": gid,
                "correct_index": correct,
                "results": results,
                "choices": choices,
                "question": g.data.get("question", ""),
                "options": g.data.get("options", []),
            })

    elif gid == "hot_takes" and action == "vote":
        choice = data.get("choice", "agree")
        g.votes[player_name] = choice
        if len(g.votes) >= len(room.connected_players):
            agree = [n for n, v in g.votes.items() if v == "agree"]
            disagree = [n for n, v in g.votes.items() if v == "disagree"]
            tied = len(agree) == len(disagree)
            if tied:
                minority = []
            else:
                minority = agree if len(agree) < len(disagree) else disagree
            await broadcast(room, {
                "type": "reveal",
                "game": gid,
                "agree": agree,
                "disagree": disagree,
                "minority": minority,
                "tied": tied,
                "take": g.data.get("take", ""),
            })

    elif gid == "taboo" and action in ("correct", "skip", "timeout"):
        word = g.data.get("word", "")
        await broadcast(room, {
            "type": "reveal",
            "game": gid,
            "result": action,
            "word": word,
            "describer": room.current_player_name(),
        })

    elif action == "next":
        room.advance_turn()
        await send_next_round(room)


# ─── WebSocket Handler ───────────────────────────────────────────────────────

@app.websocket("/ws/{room_code}/{player_name}")
async def websocket_endpoint(ws: WebSocket, room_code: str, player_name: str):
    await ws.accept()

    # Create or join room
    if room_code == "NEW":
        code = generate_code()
        room = Room(code=code)
        rooms[code] = room
        player = Player(name=player_name, ws=ws, is_host=True, connected=True)
        room.players.append(player)
        await send(ws, {"type": "room_created", "room_code": code})
    else:
        code = room_code.upper()
        room = rooms.get(code)
        if not room:
            await send(ws, {"type": "error", "message": "Room not found"})
            await ws.close()
            return

        existing = room.get_player(player_name)
        if existing:
            existing.ws = ws
            existing.connected = True
            player = existing
            # Cancel host transfer if the host just reconnected
            if player.is_host:
                _cancel_host_transfer(room)
        else:
            player = Player(name=player_name, ws=ws, connected=True)
            room.players.append(player)

    room.last_activity = time.time()

    await broadcast_lobby(room)
    await send(ws, {
        "type": "game_catalog",
        "games": GAME_CATALOG,
    })

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")
            room.last_activity = time.time()

            if msg_type == "toggle_spicy":
                if player.is_host or player == room.host:
                    room.spicy_mode = not room.spicy_mode
                    room.decks.clear()
                    await broadcast_lobby(room)

            elif msg_type == "start_game":
                game_id = data.get("game_id", "")
                if player.is_host or player == room.host:
                    await start_game(room, game_id)

            elif msg_type == "game_action":
                await handle_game_action(room, player_name, data)

            elif msg_type == "chat":
                await broadcast(room, {
                    "type": "chat",
                    "player": player_name,
                    "message": data.get("message", ""),
                })

            elif msg_type == "transfer_host":
                target_name = data.get("target", "")
                if (player.is_host or player == room.host) and target_name:
                    target = room.get_player(target_name)
                    if target and target.connected and target != player:
                        player.is_host = False
                        target.is_host = True
                        await broadcast_lobby(room)
                        await broadcast(room, {
                            "type": "host_transferred",
                            "old_host": player.name,
                            "new_host": target.name,
                        })

            elif msg_type == "leave_room":
                player.connected = False
                player.ws = None
                room.players = [p for p in room.players if p.name != player.name]
                room.last_activity = time.time()
                if player.is_host and room.connected_players:
                    new_host = room.connected_players[0]
                    new_host.is_host = True
                    await broadcast_lobby(room)
                    await broadcast(room, {
                        "type": "host_transferred",
                        "old_host": player.name,
                        "new_host": new_host.name,
                    })
                elif room.connected_players:
                    await broadcast_lobby(room)
                await broadcast(room, {
                    "type": "player_left",
                    "player": player.name,
                    "new_host": room.host.name if room.host else "",
                })
                await ws.close()
                return

            elif msg_type == "return_to_lobby":
                if player.is_host or player == room.host:
                    room.game = GameState()
                    await broadcast_lobby(room)
                    await broadcast(room, {"type": "return_to_lobby"})

    except WebSocketDisconnect:
        player.connected = False
        player.ws = None
        room.last_activity = time.time()
        if room.connected_players:
            # If the disconnected player was host, start transfer timer
            if player.is_host:
                _schedule_host_transfer(room, player)
            await broadcast_lobby(room)
            await broadcast(room, {
                "type": "player_left",
                "player": player_name,
                "new_host": room.host.name if room.host else "",
            })


# ─── Host Transfer Timer ─────────────────────────────────────────────────────

def _schedule_host_transfer(room: Room, old_host: Player) -> None:
    """Start a 2-min timer to transfer host if they don't reconnect."""
    if room._host_transfer_task and not room._host_transfer_task.done():
        room._host_transfer_task.cancel()
    room._host_transfer_task = asyncio.create_task(
        _host_transfer_countdown(room, old_host)
    )

async def _host_transfer_countdown(room: Room, old_host: Player) -> None:
    try:
        await asyncio.sleep(HOST_TRANSFER_SECONDS)
        # If old host still disconnected, transfer
        if not old_host.connected:
            old_host.is_host = False
            new_host = room.host  # picks first connected player
            if new_host:
                new_host.is_host = True
                await broadcast_lobby(room)
                await broadcast(room, {
                    "type": "host_transferred",
                    "old_host": old_host.name,
                    "new_host": new_host.name,
                })
    except asyncio.CancelledError:
        pass

def _cancel_host_transfer(room: Room) -> None:
    if room._host_transfer_task and not room._host_transfer_task.done():
        room._host_transfer_task.cancel()
        room._host_transfer_task = None


# ─── Room Cleanup ────────────────────────────────────────────────────────────

async def cleanup_rooms():
    """Periodically remove empty rooms and inactive rooms (30 min timeout)."""
    while True:
        await asyncio.sleep(60)
        now = time.time()
        expired = []
        for code, room in rooms.items():
            if not room.connected_players and (now - room.last_activity) > ROOM_EXPIRY_SECONDS:
                expired.append(code)
            elif (now - room.last_activity) > INACTIVITY_TIMEOUT:
                asyncio.create_task(broadcast(room, {
                    "type": "room_closed",
                    "reason": "Room closed due to 30 minutes of inactivity.",
                }))
                expired.append(code)
        for code in expired:
            rooms.pop(code, None)

@app.on_event("startup")
async def startup():
    init_db()
    seed_from_game_data()
    asyncio.create_task(cleanup_rooms())


# ─── Static Files ────────────────────────────────────────────────────────────

class ContentPayload(BaseModel):
    game: str
    pool: str = "normal"
    items: list


@app.get("/api/content")
async def api_content_list(game: str | None = None):
    return JSONResponse(count_content(game))


@app.get("/api/content/{game}/{pool}")
async def api_content_get(game: str, pool: str = "normal"):
    items = get_content(game, pool)
    return JSONResponse({"game": game, "pool": pool, "count": len(items), "items": items})


@app.post("/api/content")
async def api_content_add(payload: ContentPayload):
    count = add_content(payload.game, payload.pool, payload.items)
    return JSONResponse({"added": count, "game": payload.game, "pool": payload.pool})


@app.put("/api/content")
async def api_content_replace(payload: ContentPayload):
    count = replace_content(payload.game, payload.pool, payload.items)
    return JSONResponse({"replaced": count, "game": payload.game, "pool": payload.pool})


@app.delete("/api/content/{game}")
async def api_content_delete(game: str, pool: str | None = None):
    count = delete_content(game, pool)
    return JSONResponse({"deleted": count, "game": game, "pool": pool})


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
