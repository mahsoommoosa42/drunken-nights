# Drunk Games Night

A multiplayer online party games website for game nights with friends. Create a room, share the code, and play together in real-time.

## Games

- **Truth or Dare** — Spill secrets or face the dare
- **Never Have I Ever** — Drink if you have done it
- **Would You Rather** — Pick between two wild options (minority drinks!)
- **Kings Cup** — Draw a card, follow the rule
- **Most Likely To** — Vote on who fits the scenario
- **Categories** — Name things in a category before time runs out
- **Trivia** — Test your boozy knowledge
- **Hot Takes** — Agree or disagree (minority drinks!)
- **Taboo** — Describe the word without saying the forbidden words
- **Two Truths & a Lie** — Guess which one is the lie
- **Rhyme Time** — Keep the rhyme chain going
- **Word Association** — Say the first word you think of

## How It Works

1. One person creates a room and gets a room code
2. Friends join using the room code
3. The host picks a game
4. Everyone plays together in real-time via WebSockets

## Tech Stack

- **Backend**: FastAPI + WebSockets (Python)
- **Frontend**: Vanilla HTML/CSS/JS
- **Real-time**: WebSocket rooms for multiplayer sync

## Running Locally

```bash
pip install fastapi uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser.

## Disclaimer

Drink responsibly. 21+ only. Know your limits.
