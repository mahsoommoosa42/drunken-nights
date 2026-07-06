/* ─── Drunk Games Night — Client ──────────────────────────────────────── */
"use strict";

// ─── State ───────────────────────────────────────────────────────────────
let ws = null;
let myName = "";
let roomCode = "";
let isHost = false;
let gameCatalog = [];
let players = [];
let currentGame = "";
let hasVoted = false;
let spicyMode = false;

// ─── DOM refs ────────────────────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const screenLanding = $("#screen-landing");
const screenCreate = $("#screen-create");
const screenJoin = $("#screen-join");
const screenLobby = $("#screen-lobby");
const screenGame = $("#screen-game");
const allScreens = [screenLanding, screenCreate, screenJoin, screenLobby, screenGame];
const toastEl = $("#toast");

// ─── Floating Icons ──────────────────────────────────────────────────────
function spawnFloatingIcons() {
  const icons = ["🍺", "🍻", "🥂", "🍷", "🍸", "🍹", "🥃", "🍾", "🌿", "💨", "🔥", "🎉", "🎲", "💀", "😵", "🫠", "🪴", "☘️"];
  const container = $("#floating-icons");
  for (let i = 0; i < 30; i++) {
    const span = document.createElement("span");
    span.className = "icon";
    span.textContent = icons[Math.floor(Math.random() * icons.length)];
    span.style.left = Math.random() * 100 + "%";
    span.style.fontSize = (1.2 + Math.random() * 2) + "rem";
    span.style.animationDuration = (12 + Math.random() * 20) + "s";
    span.style.animationDelay = (-Math.random() * 30) + "s";
    container.appendChild(span);
  }
}
spawnFloatingIcons();

// ─── Screens ─────────────────────────────────────────────────────────────
function showScreen(el) {
  allScreens.forEach(s => s.classList.remove("active"));
  el.classList.add("active");
  window.scrollTo(0, 0);
}

// ─── Toast ───────────────────────────────────────────────────────────────
function toast(msg, duration = 3000) {
  toastEl.textContent = msg;
  toastEl.classList.add("show");
  setTimeout(() => toastEl.classList.remove("show"), duration);
}

// ─── Session Persistence (localStorage) ──────────────────────────────────
function saveSession(code, name) {
  const sessions = JSON.parse(localStorage.getItem("dgn_sessions") || "[]");
  const existing = sessions.find(s => s.code === code && s.name === name);
  if (!existing) sessions.push({ code, name, ts: Date.now() });
  else existing.ts = Date.now();
  localStorage.setItem("dgn_sessions", JSON.stringify(sessions));
}

function removeSession(code, name) {
  let sessions = JSON.parse(localStorage.getItem("dgn_sessions") || "[]");
  sessions = sessions.filter(s => !(s.code === code && s.name === name));
  localStorage.setItem("dgn_sessions", JSON.stringify(sessions));
}

function getSavedSessions() {
  return JSON.parse(localStorage.getItem("dgn_sessions") || "[]");
}

// ─── WebSocket ───────────────────────────────────────────────────────────
let reconnectAttempts = 0;
let intentionalClose = false;

function connect(code, name) {
  intentionalClose = false;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const url = `${proto}://${location.host}/ws/${code}/${name}`;
  ws = new WebSocket(url);
  ws.onopen = () => {
    toast("Connected!");
    reconnectAttempts = 0;
  };
  ws.onclose = () => {
    if (!intentionalClose && roomCode && myName) {
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
      reconnectAttempts++;
      toast(`Disconnected — reconnecting in ${Math.round(delay/1000)}s...`);
      setTimeout(() => {
        if (!intentionalClose) connect(roomCode, myName);
      }, delay);
    } else {
      toast("Disconnected from room");
    }
  };
  ws.onerror = () => {};
  ws.onmessage = (e) => handleMessage(JSON.parse(e.data));
}

function wsSend(data) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(data));
}

// ─── Rejoin UI ───────────────────────────────────────────────────────────
async function loadRejoinList() {
  const sessions = getSavedSessions();
  if (sessions.length === 0) {
    $("#rejoin-section").style.display = "none";
    return;
  }
  try {
    const resp = await fetch("/api/room_status", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ rooms: sessions }),
    });
    const active = await resp.json();
    const list = $("#rejoin-list");
    list.innerHTML = "";
    if (active.length === 0) {
      $("#rejoin-section").style.display = "none";
      // Clean up stale sessions
      sessions.forEach(s => removeSession(s.code, s.name));
      return;
    }
    $("#rejoin-section").style.display = "";
    active.forEach(s => {
      const card = document.createElement("div");
      card.className = "rejoin-card";
      card.innerHTML = `
        <div class="rejoin-info">
          <span class="rejoin-code">${s.code}</span>
          <span class="rejoin-detail">${s.players} online${s.game ? ' · Playing ' + s.game.replace(/_/g, ' ') : ''}</span>
        </div>
        <button class="btn btn-sm btn-primary rejoin-btn" data-code="${s.code}" data-name="${s.name}">Rejoin as ${s.name}</button>
      `;
      list.appendChild(card);
    });
    list.querySelectorAll(".rejoin-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        myName = btn.dataset.name;
        connect(btn.dataset.code, myName);
      });
    });
    // Clean up sessions that are no longer active
    const activeCodes = new Set(active.map(a => a.code + "|" + a.name));
    sessions.forEach(s => {
      if (!activeCodes.has(s.code + "|" + s.name)) removeSession(s.code, s.name);
    });
  } catch (e) {
    $("#rejoin-section").style.display = "none";
  }
}
loadRejoinList();

// ─── Message Router ──────────────────────────────────────────────────────
function handleMessage(msg) {
  switch (msg.type) {
    case "room_created":
      roomCode = msg.room_code;
      break;
    case "error":
      toast(msg.message);
      if (msg.message === "Room not found") {
        intentionalClose = true;
        removeSession(roomCode, myName);
        roomCode = "";
        showScreen(screenLanding);
        loadRejoinList();
      }
      break;
    case "lobby":
      roomCode = msg.room_code;
      players = msg.players;
      isHost = msg.host === myName;
      spicyMode = msg.spicy_mode || false;
      saveSession(roomCode, myName);
      renderLobby(msg);
      renderSpicyToggle();
      if (gameCatalog.length > 0) renderGameGrid();
      if (!screenLobby.classList.contains("active") && !screenGame.classList.contains("active")) showScreen(screenLobby);
      break;
    case "game_catalog":
      gameCatalog = msg.games;
      renderGameGrid();
      break;
    case "game_start":
      currentGame = msg.game_id;
      hasVoted = false;
      hideHostTracker();
      const info = gameCatalog.find(g => g.id === msg.game_id);
      $("#game-title").textContent = info ? `${info.emoji} ${info.name}` : msg.game_id;
      showScreen(screenGame);
      break;
    case "round":
      hasVoted = false;
      hideHostTracker();
      renderRound(msg);
      break;
    case "reveal":
      hideHostTracker();
      renderReveal(msg);
      break;
    case "answer_progress":
      renderAnswerProgress(msg);
      break;
    case "vote_update":
      renderVoteUpdate(msg);
      break;
    case "return_to_lobby":
      currentGame = "";
      hideHostTracker();
      showScreen(screenLobby);
      break;
    case "player_left":
      toast(`${msg.player} left the room`);
      if (msg.new_host === myName) {
        isHost = true;
        toast("You are now the host!");
      }
      break;
    case "player_disconnected":
      toast(`${msg.player} disconnected`);
      if (msg.new_host === myName) {
        isHost = true;
        toast("You are now the host!");
      }
      break;
    case "player_reconnected":
      toast(`${msg.player} reconnected!`);
      break;
    case "rejoin_state":
      toast(msg.message || "Rejoined game in progress!", 3000);
      break;
    case "host_transferred":
      if (msg.new_host === myName) {
        isHost = true;
        toast(`🎉 You are now the host! (${msg.old_host} transferred host)`, 5000);
        renderSpicyToggle();
        renderHostControls();
        if (gameCatalog.length > 0) renderGameGrid();
      } else {
        isHost = (msg.new_host === myName);
        toast(`${msg.new_host} is now the host`);
        renderHostControls();
      }
      break;
    case "room_closed":
      toast(msg.reason || "Room has been closed.", 5000);
      intentionalClose = true;
      removeSession(roomCode, myName);
      if (ws) ws.close();
      showScreen(screenLanding);
      loadRejoinList();
      break;
    case "chat":
      // Future: in-game chat
      break;
  }
}

// ─── Navigation Buttons ──────────────────────────────────────────────────
$("#btn-go-create").addEventListener("click", () => showScreen(screenCreate));
$("#btn-go-join").addEventListener("click", () => showScreen(screenJoin));
$("#btn-back-create").addEventListener("click", () => showScreen(screenLanding));
$("#btn-back-join").addEventListener("click", () => showScreen(screenLanding));

// ─── Create / Join Buttons ───────────────────────────────────────────────
$("#btn-create").addEventListener("click", () => {
  const name = $("#input-name-create").value.trim();
  if (!name) { toast("Enter your name!"); return; }
  myName = name;
  connect("NEW", name);
});

$("#btn-join").addEventListener("click", () => {
  const name = $("#input-name-join").value.trim();
  const code = $("#input-code").value.trim().toUpperCase();
  if (!name) { toast("Enter your name!"); return; }
  if (!code || code.length < 4) { toast("Enter a valid room code!"); return; }
  myName = name;
  connect(code, name);
});

$("#input-name-create").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("#btn-create").click();
});
$("#input-code").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("#btn-join").click();
});
$("#input-name-join").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("#input-code").focus();
});

$("#btn-back-lobby").addEventListener("click", () => {
  if (isHost) wsSend({ type: "return_to_lobby" });
  else toast("Only the host can return to lobby");
});

// Transfer host
$("#btn-transfer-host").addEventListener("click", () => {
  const target = $("#transfer-target").value;
  if (!target) return;
  wsSend({ type: "transfer_host", target });
});

// Leave room
$("#btn-leave-room").addEventListener("click", () => {
  if (confirm("Leave this room?")) {
    intentionalClose = true;
    wsSend({ type: "leave_room" });
    removeSession(roomCode, myName);
    showScreen(screenLanding);
    loadRejoinList();
  }
});

// Copy room link
$("#btn-copy-link").addEventListener("click", () => {
  const url = `${location.origin}?room=${roomCode}`;
  navigator.clipboard.writeText(url).then(() => {
    toast("Link copied!");
    $("#btn-copy-link").textContent = "Copied!";
    setTimeout(() => { $("#btn-copy-link").textContent = "📋 Copy Link"; }, 2000);
  }).catch(() => toast("Failed to copy"));
});

// Auto-fill room code from URL and go straight to Join screen
(function prefillRoom() {
  const params = new URLSearchParams(location.search);
  const code = params.get("room");
  if (code) {
    $("#input-code").value = code.toUpperCase();
    showScreen(screenJoin);
  }
})();

// ─── Lobby Rendering ─────────────────────────────────────────────────────
function renderLobby(msg) {
  $("#lobby-code").textContent = msg.room_code;
  const list = $("#player-list");
  list.innerHTML = "";
  const allPlayers = msg.all_players || msg.players.map(n => ({name: n, connected: true}));
  allPlayers.forEach(p => {
    const chip = document.createElement("div");
    chip.className = "player-chip" + (p.connected ? "" : " player-disconnected");
    let label = p.name || p;
    const name = p.name || p;
    if (name === msg.host) label += ' <span class="host-badge">HOST</span>';
    if (!p.connected) label += ' <span class="dc-badge">offline</span>';
    chip.innerHTML = label;
    list.appendChild(chip);
  });
  renderHostControls();
}

function renderHostControls() {
  const wrap = $("#host-controls");
  const select = $("#transfer-target");
  if (!isHost || players.length < 2) {
    wrap.style.display = "none";
    return;
  }
  wrap.style.display = "flex";
  select.innerHTML = "";
  players.filter(n => n !== myName).forEach(name => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    select.appendChild(opt);
  });
}

function renderGameGrid() {
  const grid = $("#game-grid");
  grid.innerHTML = "";
  gameCatalog.forEach(g => {
    const tile = document.createElement("div");
    const disabled = players.length < g.min_players;
    tile.className = "game-tile" + (disabled ? " disabled" : "");
    tile.innerHTML = `
      <div class="tile-emoji">${g.emoji}</div>
      <div class="tile-name">${g.name}</div>
      <div class="tile-desc">${g.desc}</div>
      ${disabled ? `<div class="tile-min">Needs ${g.min_players}+ players</div>` : ""}
    `;
    if (!disabled) {
      tile.addEventListener("click", () => {
        if (!isHost) { toast("Only the host can start a game"); return; }
        wsSend({ type: "start_game", game_id: g.id });
      });
    }
    grid.appendChild(tile);
  });
}

// ─── Spicy Mode Toggle ──────────────────────────────────────────────────
function renderSpicyToggle() {
  const wrap = $("#spicy-toggle-wrap");
  const btn = $("#btn-spicy-toggle");
  const icon = $("#spicy-icon");
  const label = $("#spicy-label");
  const hint = $("#spicy-hint");
  wrap.style.display = "";
  if (spicyMode) {
    btn.classList.add("active");
    icon.textContent = "🔥";
    label.textContent = "18+ Mode ON";
    hint.textContent = "Spicy prompts are mixed in!";
  } else {
    btn.classList.remove("active");
    icon.textContent = "🌶️";
    label.textContent = "Enable 18+ Mode";
    hint.textContent = "Only the host can toggle this";
  }
  btn.disabled = !isHost;
  btn.style.opacity = isHost ? "1" : "0.5";
  btn.style.cursor = isHost ? "pointer" : "not-allowed";
}

$("#btn-spicy-toggle").addEventListener("click", () => {
  if (!isHost) { toast("Only the host can toggle 18+ mode"); return; }
  wsSend({ type: "toggle_spicy" });
});

// ─── Round Rendering ─────────────────────────────────────────────────────
function renderRound(msg) {
  const area = $("#game-area");
  const gid = msg.game;
  const isMyturn = msg.current_player === myName;

  if (gid === "truth_or_dare") {
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">${msg.current_player}'s turn</div>
        <div class="prompt">Truth or Dare?</div>
        ${isMyturn ? `
          <div class="btn-row">
            <button class="btn btn-primary" onclick="pickTod('truth')">🤫 Truth</button>
            <button class="btn btn-pink" onclick="pickTod('dare')">😈 Dare</button>
          </div>
        ` : `<p class="waiting-text">Waiting for ${msg.current_player} to choose...</p>`}
      </div>
    `;
  }

  else if (gid === "never_have_i_ever") {
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">Never Have I Ever</div>
        <div class="prompt">${msg.statement}</div>
        <p class="sub-text">Tap if you HAVE done it — drinkers beware!</p>
        <div class="btn-row">
          <button class="btn btn-red" id="nhie-drank" onclick="nhieVote(true)">🍺 I Have (Drink!)</button>
          <button class="btn btn-green" id="nhie-safe" onclick="nhieVote(false)">😇 Never</button>
        </div>
      </div>
    `;
  }

  else if (gid === "would_you_rather") {
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">Would You Rather</div>
        <div class="btn-row" style="margin-top:1rem">
          <button class="option-btn" id="wyr-a" onclick="wyrVote('a')">${msg.option_a}</button>
          <button class="option-btn" id="wyr-b" onclick="wyrVote('b')">${msg.option_b}</button>
        </div>
        <p class="sub-text" style="margin-top:1rem">Minority drinks!</p>
      </div>
    `;
  }

  else if (gid === "kings_cup") {
    const isRed = msg.suit === "hearts" || msg.suit === "diamonds";
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">${msg.current_player} drew a card</div>
        <div class="playing-card ${isRed ? 'red' : ''}">
          <span class="card-value">${msg.card}</span>
          <span class="card-suit">${msg.suit_symbol}</span>
        </div>
        <div class="prompt">${msg.rule_name}</div>
        <p class="sub-text">${msg.rule}</p>
        <p class="vote-status">Kings drawn: ${msg.kings_drawn}/4</p>
        ${isHost ? '<div class="btn-row"><button class="btn btn-primary" onclick="nextRound()">Next Card</button></div>' : ''}
      </div>
    `;
  }

  else if (gid === "most_likely_to") {
    const btns = msg.players.map(name =>
      `<button class="option-btn" onclick="mltVote('${esc(name)}')">${escHtml(name)}</button>`
    ).join("");
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">Most Likely To</div>
        <div class="prompt">${msg.scenario}</div>
        <p class="sub-text">Vote for who's most likely!</p>
        <div class="btn-row" id="mlt-btns">${btns}</div>
        <p class="vote-status" id="vote-status"></p>
      </div>
    `;
  }

  else if (gid === "categories") {
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">Categories</div>
        <div class="prompt">${msg.category}</div>
        <p class="sub-text">Go around naming things! First person who can't think of one drinks.</p>
        <div class="timer" id="cat-timer">${msg.timer_seconds}s</div>
        ${isHost ? '<div class="btn-row"><button class="btn btn-primary" onclick="nextRound()">Next Category</button></div>' : ''}
      </div>
    `;
    startTimer(msg.timer_seconds, "cat-timer");
  }

  else if (gid === "trivia") {
    const opts = msg.options.map((opt, i) =>
      `<button class="option-btn" id="triv-${i}" onclick="triviaAnswer(${i})">${opt}</button>`
    ).join("");
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">Trivia</div>
        <div class="prompt">${msg.question}</div>
        <div class="trivia-grid" id="trivia-opts">${opts}</div>
        <p class="sub-text" id="vote-status"></p>
      </div>
    `;
  }

  else if (gid === "hot_takes") {
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">Hot Take</div>
        <div class="prompt">"${msg.take}"</div>
        <p class="sub-text">Minority drinks!</p>
        <div class="btn-row">
          <button class="btn btn-green" id="ht-agree" onclick="hotTakeVote('agree')">👍 Agree</button>
          <button class="btn btn-red" id="ht-disagree" onclick="hotTakeVote('disagree')">👎 Disagree</button>
        </div>
      </div>
    `;
  }

  else if (gid === "taboo") {
    if (msg.role === "describer") {
      const chips = msg.forbidden.map(w => `<span class="forbidden-chip">${w}</span>`).join("");
      area.innerHTML = `
        <div class="game-card">
          <div class="turn-label">You're describing!</div>
          <div class="taboo-word">${msg.word}</div>
          <p class="sub-text">Don't say these words:</p>
          <div class="forbidden-list">${chips}</div>
          <div class="timer" id="taboo-timer">${msg.timer_seconds}s</div>
          <div class="btn-row">
            <button class="btn btn-green" onclick="tabooResult('correct')">They got it!</button>
            <button class="btn btn-orange" onclick="tabooResult('skip')">Skip</button>
            <button class="btn btn-red" onclick="tabooResult('timeout')">Time's up</button>
          </div>
        </div>
      `;
      startTimer(msg.timer_seconds, "taboo-timer");
    } else {
      area.innerHTML = `
        <div class="game-card">
          <div class="turn-label">${msg.current_player} is describing</div>
          <div class="prompt">🤔 Guess the word!</div>
          <div class="timer" id="taboo-timer">${msg.timer_seconds}s</div>
          <p class="waiting-text">Listen and guess...</p>
        </div>
      `;
      startTimer(msg.timer_seconds, "taboo-timer");
    }
  }

  else if (gid === "two_truths") {
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">${msg.current_player}'s turn</div>
        <div class="prompt">${msg.prompt}</div>
        <p class="sub-text">${isMyturn
          ? "Tell the group your two truths and a lie — in any order!"
          : `Listen to ${msg.current_player} and try to spot the lie!`}</p>
        ${isHost ? '<div class="btn-row"><button class="btn btn-primary" onclick="nextRound()">Next Player</button></div>' : ''}
      </div>
    `;
  }

  else if (gid === "rhyme_time") {
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">Rhyme Time</div>
        <div class="prompt" style="font-size:2.5rem; color:var(--accent)">${msg.starter_word}</div>
        <p class="sub-text">Go around saying words that rhyme! First person who can't drinks.</p>
        ${isHost ? '<div class="btn-row"><button class="btn btn-primary" onclick="nextRound()">New Word</button></div>' : ''}
      </div>
    `;
  }

  else if (gid === "word_association") {
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">Word Association</div>
        <div class="prompt" style="font-size:2.5rem; color:var(--accent2)">${msg.starter_word}</div>
        <p class="sub-text">Say the first word that comes to mind! Hesitate or repeat = drink!</p>
        ${isHost ? '<div class="btn-row"><button class="btn btn-primary" onclick="nextRound()">New Word</button></div>' : ''}
      </div>
    `;
  }
}

// ─── Reveal Rendering ────────────────────────────────────────────────────
function renderReveal(msg) {
  const area = $("#game-area");
  const gid = msg.game;

  if (gid === "truth_or_dare") {
    const label = msg.choice === "truth" ? "🤫 Truth" : "😈 Dare";
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">${msg.player} chose ${msg.choice}</div>
        <div class="prompt">${msg.prompt}</div>
        <div class="drink-banner">${msg.choice === "truth" ? "Refuse to answer? DRINK!" : "Refuse the dare? DRINK TWICE!"}</div>
        ${isHost ? '<div class="btn-row"><button class="btn btn-primary" onclick="nextRound()">Next Turn</button></div>' : ''}
      </div>
    `;
  }

  else if (gid === "never_have_i_ever") {
    const drinkerTags = msg.drinkers.map(n => `<span class="name-tag drinker">${n} 🍺</span>`).join("");
    const safeTags = players.filter(n => !msg.drinkers.includes(n)).map(n => `<span class="name-tag winner">${n} 😇</span>`).join("");
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">Results</div>
        ${msg.drinkers.length > 0 ? `
          <div class="result-section">
            <div class="result-label">Drinkers (${msg.drinkers.length})</div>
            <div class="result-names">${drinkerTags}</div>
          </div>
        ` : '<div class="prompt">Nobody? Bunch of saints! 😇</div>'}
        ${safeTags ? `
          <div class="result-section">
            <div class="result-label">Safe</div>
            <div class="result-names">${safeTags}</div>
          </div>
        ` : ''}
        ${isHost ? '<div class="btn-row"><button class="btn btn-primary" onclick="nextRound()">Next Round</button></div>' : ''}
      </div>
    `;
  }

  else if (gid === "would_you_rather") {
    const aNames = msg.a_voters.map(n => `<span class="name-tag">${n}</span>`).join("");
    const bNames = msg.b_voters.map(n => `<span class="name-tag">${n}</span>`).join("");
    const minNames = msg.minority.map(n => `<span class="name-tag drinker">${n} 🍺</span>`).join("");
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">Results</div>
        <div class="result-section">
          <div class="result-label">${msg.option_a} (${msg.a_voters.length})</div>
          <div class="result-names">${aNames || '<em>Nobody</em>'}</div>
        </div>
        <div class="result-section">
          <div class="result-label">${msg.option_b} (${msg.b_voters.length})</div>
          <div class="result-names">${bNames || '<em>Nobody</em>'}</div>
        </div>
        ${msg.minority.length > 0 ? `
          <div class="drink-banner">Minority drinks!</div>
          <div class="result-section">
            <div class="result-names">${minNames}</div>
          </div>
        ` : '<div class="drink-banner">It\'s a tie! Everyone drinks!</div>'}
        ${isHost ? '<div class="btn-row"><button class="btn btn-primary" onclick="nextRound()">Next Round</button></div>' : ''}
      </div>
    `;
  }

  else if (gid === "most_likely_to") {
    const sorted = Object.entries(msg.tally).sort((a, b) => b[1] - a[1]);
    const rows = sorted.map(([name, count]) => {
      const isWinner = msg.winners.includes(name);
      return `<div class="result-section" style="padding-top:.5rem; border:none;">
        <span class="name-tag ${isWinner ? 'drinker' : ''}">${name}: ${count} vote${count > 1 ? 's' : ''} ${isWinner ? '🍺' : ''}</span>
      </div>`;
    }).join("");
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">Most Likely To</div>
        <div class="prompt" style="font-size:1.1rem">${msg.scenario}</div>
        ${rows}
        <div class="drink-banner">${msg.winners.join(" & ")} — DRINK!</div>
        ${isHost ? '<div class="btn-row"><button class="btn btn-primary" onclick="nextRound()">Next Round</button></div>' : ''}
      </div>
    `;
  }

  else if (gid === "trivia") {
    const correct = msg.correct_index;
    const opts = msg.options || [];
    const wrongPlayers = Object.entries(msg.results).filter(([,v]) => !v).map(([n]) => n);
    const rightPlayers = Object.entries(msg.results).filter(([,v]) => v).map(([n]) => n);

    // Build per-option breakdown showing who picked what
    const optBreakdown = (opts.length > 0 ? opts : ["A","B","C","D"]).map((opt, i) => {
      const pickers = Object.entries(msg.choices || {}).filter(([,c]) => c === i).map(([n]) => n);
      const isCorrect = i === correct;
      return pickers.length > 0 ? `<div class="result-section" style="padding:.4rem 0;border:none;">
        <div class="result-label" style="font-size:.85rem;">${isCorrect ? '✅' : '❌'} ${opt}</div>
        <div class="result-names">${pickers.map(n => `<span class="name-tag ${isCorrect ? '' : 'drinker'}">${n}</span>`).join("")}</div>
      </div>` : '';
    }).join("");

    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">Trivia Results</div>
        <div class="prompt" style="font-size:1.1rem">${msg.question || ''}</div>
        ${optBreakdown}
        ${wrongPlayers.length > 0
          ? `<div class="drink-banner">${wrongPlayers.join(", ")} — DRINK!</div>`
          : '<div class="drink-banner" style="color:var(--green)">Everyone got it right! 🎉</div>'}
        ${isHost ? '<div class="btn-row" style="margin-top:1rem"><button class="btn btn-primary" onclick="nextRound()">Next Question</button></div>' : ''}
      </div>
    `;
  }

  else if (gid === "hot_takes") {
    const agreeNames = msg.agree.map(n => `<span class="name-tag">${n}</span>`).join("");
    const disagreeNames = msg.disagree.map(n => `<span class="name-tag">${n}</span>`).join("");
    const minNames = msg.minority.map(n => `<span class="name-tag drinker">${n} 🍺</span>`).join("");
    const allNames = [...msg.agree, ...msg.disagree].map(n => `<span class="name-tag drinker">${n} 🍺</span>`).join("");
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">Hot Take Results</div>
        <div class="prompt" style="font-size:1.1rem">"${msg.take}"</div>
        <div class="result-section">
          <div class="result-label">👍 Agree (${msg.agree.length})</div>
          <div class="result-names">${agreeNames || '<em>Nobody</em>'}</div>
        </div>
        <div class="result-section">
          <div class="result-label">👎 Disagree (${msg.disagree.length})</div>
          <div class="result-names">${disagreeNames || '<em>Nobody</em>'}</div>
        </div>
        ${msg.tied
          ? `<div class="drink-banner">It's a tie! Everyone drinks!</div><div class="result-section"><div class="result-names">${allNames}</div></div>`
          : `<div class="drink-banner">Minority drinks!</div><div class="result-section"><div class="result-names">${minNames}</div></div>`}
        ${isHost ? '<div class="btn-row"><button class="btn btn-primary" onclick="nextRound()">Next Take</button></div>' : ''}
      </div>
    `;
  }

  else if (gid === "taboo") {
    const emoji = msg.result === "correct" ? "🎉" : msg.result === "skip" ? "⏭️" : "⏰";
    const label = msg.result === "correct" ? "They got it!" : msg.result === "skip" ? "Skipped!" : "Time's up!";
    const drink = msg.result === "correct"
      ? `Everyone else drinks for missing it!`
      : `${msg.describer} drinks!`;
    area.innerHTML = `
      <div class="game-card">
        <div class="turn-label">${emoji} ${label}</div>
        <div class="taboo-word">${msg.word}</div>
        <div class="drink-banner">${drink}</div>
        ${isHost ? '<div class="btn-row"><button class="btn btn-primary" onclick="nextRound()">Next Word</button></div>' : ''}
      </div>
    `;
  }
}

// ─── Vote update ─────────────────────────────────────────────────────────
function renderVoteUpdate(msg) {
  const el = document.getElementById("vote-status");
  if (el) el.textContent = `${msg.votes_in}/${msg.total} votes in...`;
}

function hideHostTracker() {
  const el = $("#host-tracker");
  if (el) {
    el.classList.add("hidden");
    el.innerHTML = "";
  }
}

function renderAnswerProgress(msg) {
  const el = $("#host-tracker");
  if (!el) return;
  if (!isHost) {
    el.classList.add("hidden");
    return;
  }
  const answered = (msg.answered || []).map(n => `<span class="track-name answered">✓ ${escHtml(n)}</span>`).join("");
  const remaining = (msg.remaining || []).map(n => `<span class="track-name pending">… ${escHtml(n)}</span>`).join("");
  el.innerHTML = `<div class="host-tracker-title">Answers ${msg.answered_count}/${msg.total}</div><div class="track-names">${answered}${remaining}</div>`;
  el.classList.remove("hidden");
}

// ─── Game Actions ────────────────────────────────────────────────────────
function pickTod(choice) {
  wsSend({ type: "game_action", action: "pick", choice });
}
window.pickTod = pickTod;

function nhieVote(drank) {
  if (hasVoted) return;
  hasVoted = true;
  wsSend({ type: "game_action", action: "drink", drank });
  if (drank) {
    $("#nhie-drank").classList.add("selected");
    $("#nhie-drank").disabled = true;
  } else {
    $("#nhie-safe").classList.add("selected");
    $("#nhie-safe").disabled = true;
  }
  $("#nhie-drank").disabled = true;
  $("#nhie-safe").disabled = true;
}
window.nhieVote = nhieVote;

function wyrVote(choice) {
  if (hasVoted) return;
  hasVoted = true;
  wsSend({ type: "game_action", action: "vote", choice });
  $(`#wyr-${choice}`).classList.add("selected");
  $("#wyr-a").disabled = true;
  $("#wyr-b").disabled = true;
}
window.wyrVote = wyrVote;

function mltVote(name) {
  if (hasVoted) return;
  hasVoted = true;
  wsSend({ type: "game_action", action: "vote", voted_for: name });
  document.querySelectorAll("#mlt-btns .option-btn").forEach(b => {
    b.disabled = true;
    if (b.textContent === name) b.classList.add("selected");
  });
}
window.mltVote = mltVote;

function triviaAnswer(idx) {
  if (hasVoted) return;
  hasVoted = true;
  wsSend({ type: "game_action", action: "answer", answer: idx });
  document.querySelectorAll("#trivia-opts .option-btn").forEach((b, i) => {
    b.disabled = true;
    if (i === idx) b.classList.add("selected");
  });
}
window.triviaAnswer = triviaAnswer;

function hotTakeVote(choice) {
  if (hasVoted) return;
  hasVoted = true;
  wsSend({ type: "game_action", action: "vote", choice });
  $(`#ht-${choice}`).classList.add("selected");
  $("#ht-agree").disabled = true;
  $("#ht-disagree").disabled = true;
}
window.hotTakeVote = hotTakeVote;

function tabooResult(result) {
  wsSend({ type: "game_action", action: result });
}
window.tabooResult = tabooResult;

function nextRound() {
  wsSend({ type: "game_action", action: "next" });
}
window.nextRound = nextRound;

// ─── Timer ───────────────────────────────────────────────────────────────
let timerInterval = null;
function startTimer(seconds, elId) {
  if (timerInterval) clearInterval(timerInterval);
  let remaining = seconds;
  const el = document.getElementById(elId);
  if (!el) return;
  timerInterval = setInterval(() => {
    remaining--;
    if (el) el.textContent = remaining + "s";
    if (remaining <= 0) {
      clearInterval(timerInterval);
      if (el) el.textContent = "Time's up!";
    }
  }, 1000);
}

// ─── Helpers ─────────────────────────────────────────────────────────────
function esc(s) { return s.replace(/'/g, "\\'"); }
function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

// ─── Bug Report ──────────────────────────────────────────────────────────
(function initBugReport() {
  const fab = $("#btn-bug-report");
  const overlay = $("#bug-report-overlay");
  const titleInput = $("#bug-title");
  const descInput = $("#bug-desc");
  const cancelBtn = $("#btn-bug-cancel");
  const submitBtn = $("#btn-bug-submit");

  fab.addEventListener("click", () => {
    overlay.classList.remove("hidden");
    titleInput.value = "";
    descInput.value = "";
    titleInput.focus();
  });

  cancelBtn.addEventListener("click", () => overlay.classList.add("hidden"));
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) overlay.classList.add("hidden");
  });

  submitBtn.addEventListener("click", async () => {
    const title = titleInput.value.trim();
    if (!title) { toast("Please enter a summary"); return; }

    submitBtn.disabled = true;
    submitBtn.textContent = "Submitting...";

    try {
      const resp = await fetch("/api/bug-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          description: descInput.value.trim(),
          room_code: roomCode || "",
          game: currentGame || "",
        }),
      });
      const data = await resp.json();
      if (data.ok) {
        toast("Bug reported — thank you!");
        overlay.classList.add("hidden");
      } else {
        toast(data.error || "Failed to submit report");
      }
    } catch {
      toast("Network error — try again");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit";
    }
  });
})();
