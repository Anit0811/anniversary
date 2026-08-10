# 💍 Love Quiz — 25th Anniversary Party Game

A live, phone-based party game for couples at a wedding anniversary celebration. Couples pair up, answer questions about themselves, then guess what their partner answered. The match percentage is their "Love Score."

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Then open **http://localhost:8000** on your phone or browser.

## How It Works

1. **One partner** taps "Start as a Couple", enters both names → gets a 4-digit room code
2. **Other partner** taps "Join with Code" and enters the code
3. **Round 1** — Each partner independently answers questions about themselves
4. **Round 2** — Each partner guesses what their partner answered (surprise twist!)
5. **Results** — See your Love Score with a fun breakdown
6. **Leaderboard** — Display on a projector for the whole party to see

## Key URLs

| URL | Purpose |
|-----|---------|
| `/` | Landing page (share via QR code) |
| `/play` | Game play page |
| `/leaderboard` | Projector display — auto-refreshing scoreboard |
| `/host-xyz123` | Host admin panel — monitor & manage |

## Deploying to Render

1. Push this repo to GitHub
2. Create a new **Web Service** on [Render](https://render.com)
3. Connect your GitHub repo
4. Render will auto-detect the `render.yaml` config
5. Deploy!

Or manually:
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Customizing Questions

Questions are seeded automatically on first run. To change them:
- Use the host panel at `/host-xyz123` to toggle questions on/off
- Or edit the `seed_questions()` function in `database.py`
- Delete `love_quiz.db` to reset everything

## Tech Stack

- **Backend:** Python, FastAPI
- **Database:** SQLite (file-based)
- **Frontend:** Jinja2 templates + vanilla JS
- **Styling:** Custom CSS with romantic color palette
