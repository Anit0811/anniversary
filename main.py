from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import secrets
import string
import datetime
import os
import aiosqlite

from database import init_db, seed_questions, get_db

app = FastAPI()

os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup_event():
    await init_db()
    await seed_questions()

class CreateCoupleReq(BaseModel):
    partner_a_name: str
    partner_b_name: str

class JoinCoupleReq(BaseModel):
    room_code: str

class AnswerReq(BaseModel):
    question_id: int
    selected_option: str
    round: int

def generate_room_code():
    return ''.join(secrets.choice(string.digits) for i in range(4))

def generate_token():
    return secrets.token_hex(16)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/play", response_class=HTMLResponse)
async def play(request: Request):
    return templates.TemplateResponse("play.html", {"request": request})

@app.get("/results/{couple_id}", response_class=HTMLResponse)
async def results_page(request: Request, couple_id: int):
    return templates.TemplateResponse("results.html", {"request": request, "couple_id": couple_id})

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    return templates.TemplateResponse("leaderboard.html", {"request": request})

@app.get("/host-xyz123", response_class=HTMLResponse)
async def host_page(request: Request):
    return templates.TemplateResponse("host.html", {"request": request})

@app.post("/api/create-couple")
async def create_couple(req: CreateCoupleReq):
    room_code = generate_room_code()
    token = generate_token()
    
    async with get_db() as db:
        cursor = await db.execute("SELECT id FROM couples WHERE room_code = ?", (room_code,))
        while await cursor.fetchone():
            room_code = generate_room_code()
            cursor = await db.execute("SELECT id FROM couples WHERE room_code = ?", (room_code,))
            
        await db.execute('''
            INSERT INTO couples (room_code, partner_a_name, partner_b_name, partner_a_token)
            VALUES (?, ?, ?, ?)
        ''', (room_code, req.partner_a_name, req.partner_b_name, token))
        await db.commit()
        
        cursor = await db.execute("SELECT id FROM couples WHERE room_code = ?", (room_code,))
        row = await cursor.fetchone()
        
    return {
        "couple_id": row["id"],
        "room_code": room_code,
        "token": token,
        "partner": "a"
    }

@app.post("/api/join-couple")
async def join_couple(req: JoinCoupleReq):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM couples WHERE room_code = ?", (req.room_code,))
        couple = await cursor.fetchone()
        
        if not couple:
            raise HTTPException(status_code=404, detail="Room not found")
            
        if couple["partner_b_token"]:
            return {
                "couple_id": couple["id"],
                "token": couple["partner_b_token"],
                "partner": "b",
                "partner_a_name": couple["partner_a_name"],
                "partner_b_name": couple["partner_b_name"]
            }
            
        token = generate_token()
        await db.execute('''
            UPDATE couples SET partner_b_token = ?, status = 'round1'
            WHERE id = ?
        ''', (token, couple["id"]))
        await db.commit()
        
    return {
        "couple_id": couple["id"],
        "token": token,
        "partner": "b",
        "partner_a_name": couple["partner_a_name"],
        "partner_b_name": couple["partner_b_name"]
    }

async def get_couple_by_token(token: str, db: aiosqlite.Connection):
    cursor = await db.execute("SELECT * FROM couples WHERE partner_a_token = ? OR partner_b_token = ?", (token, token))
    couple = await cursor.fetchone()
    if not couple:
        return None, None
    partner = "a" if couple["partner_a_token"] == token else "b"
    return couple, partner

@app.get("/api/status")
async def get_status(token: str = None):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    async with get_db() as db:
        couple, partner = await get_couple_by_token(token, db)
        if not couple:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        cursor = await db.execute("SELECT COUNT(*) as count FROM questions WHERE active = 1")
        row = await cursor.fetchone()
        total_questions = row["count"]
        
        current_round = 1 if couple["status"] == "round1" else (2 if couple["status"] == "round2" else (3 if couple["status"] == "done" else 0))
        if couple["status"] == "pairing":
            current_round = 0
            
        active_round = 1
        if couple[f"partner_{partner}_round1_done"]:
            active_round = 2
        if couple[f"partner_{partner}_round2_done"]:
            active_round = 3
            
        cursor = await db.execute("SELECT COUNT(*) as count FROM answers WHERE couple_id = ? AND partner = ? AND round = ?", (couple["id"], partner, active_round))
        ans_row = await cursor.fetchone()
        answered_count = ans_row["count"] if ans_row else 0
        
        return {
            "couple_id": couple["id"],
            "status": couple["status"],
            "partner": partner,
            "partner_name": couple[f"partner_{partner}_name"],
            "other_partner_name": couple["partner_b_name"] if partner == "a" else couple["partner_a_name"],
            "current_round": active_round,
            "total_questions": total_questions,
            "questions_answered_count": answered_count,
            "room_code": couple["room_code"],
            "partner_a_round1_done": couple["partner_a_round1_done"],
            "partner_b_round1_done": couple["partner_b_round1_done"],
            "partner_a_round2_done": couple["partner_a_round2_done"],
            "partner_b_round2_done": couple["partner_b_round2_done"],
        }

@app.get("/api/questions")
async def get_questions(round: int, token: str = None):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    async with get_db() as db:
        couple, partner = await get_couple_by_token(token, db)
        if not couple:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        cursor = await db.execute("SELECT * FROM questions WHERE active = 1")
        questions = await cursor.fetchall()
        
        res = []
        other_name = couple["partner_b_name"] if partner == "a" else couple["partner_a_name"]
        
        for q in questions:
            text = q["text"]
            if round == 2:
                text = f"What did {other_name} answer for: '{text}'"
                
            res.append({
                "id": q["id"],
                "text": text,
                "option_a": q["option_a"],
                "option_b": q["option_b"],
                "option_c": q["option_c"],
                "option_d": q["option_d"],
                "is_bonus": q["is_bonus"]
            })
            
        return res

async def calculate_love_score(couple_id: int, db: aiosqlite.Connection):
    cursor = await db.execute("SELECT * FROM answers WHERE couple_id = ?", (couple_id,))
    answers = await cursor.fetchall()
    
    cursor = await db.execute("SELECT id, is_bonus FROM questions WHERE active = 1")
    questions = await cursor.fetchall()
    scored_q_ids = [q["id"] for q in questions if not q["is_bonus"]]
    num_scored = len(scored_q_ids)
    
    if num_scored == 0:
        return 0
        
    matches = 0
    ans_dict = {(a["partner"], a["round"], a["question_id"]): a["selected_option"] for a in answers}
    
    for q_id in scored_q_ids:
        a_r2 = ans_dict.get(("a", 2, q_id))
        b_r1 = ans_dict.get(("b", 1, q_id))
        if a_r2 and b_r1 and a_r2 == b_r1:
            matches += 1
            
        b_r2 = ans_dict.get(("b", 2, q_id))
        a_r1 = ans_dict.get(("a", 1, q_id))
        if b_r2 and a_r1 and b_r2 == a_r1:
            matches += 1
            
    score = (matches / (2 * num_scored)) * 100
    
    await db.execute("UPDATE couples SET love_score = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?", (score, couple_id))
    await db.commit()
    return score

@app.post("/api/answer")
async def submit_answer(req: AnswerReq, token: str = None):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    if req.round not in (1, 2):
        raise HTTPException(status_code=400, detail="Invalid round")
    async with get_db() as db:
        couple, partner = await get_couple_by_token(token, db)
        if not couple:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Validate the couple is in the correct status for this round
        expected_status = "round1" if req.round == 1 else "round2"
        if couple["status"] != expected_status:
            raise HTTPException(status_code=400, detail="Not in the right round")
            
        cursor = await db.execute("SELECT id FROM answers WHERE couple_id = ? AND partner = ? AND question_id = ? AND round = ?", 
                                 (couple["id"], partner, req.question_id, req.round))
        if await cursor.fetchone():
            raise HTTPException(status_code=400, detail="Already answered")
            
        await db.execute('''
            INSERT INTO answers (couple_id, partner, question_id, round, selected_option)
            VALUES (?, ?, ?, ?, ?)
        ''', (couple["id"], partner, req.question_id, req.round, req.selected_option))
        await db.commit()
        
        cursor = await db.execute("SELECT COUNT(*) as count FROM questions WHERE active = 1")
        total_q = (await cursor.fetchone())["count"]
        
        cursor = await db.execute("SELECT COUNT(*) as count FROM answers WHERE couple_id = ? AND partner = ? AND round = ?", 
                                 (couple["id"], partner, req.round))
        ans_count = (await cursor.fetchone())["count"]
        
        if ans_count >= total_q:
            # Mark this partner's round as done using explicit column names
            done_col = f"partner_{partner}_round{req.round}_done"
            if done_col in ("partner_a_round1_done", "partner_b_round1_done", "partner_a_round2_done", "partner_b_round2_done"):
                await db.execute(f"UPDATE couples SET {done_col} = 1 WHERE id = ?", (couple["id"],))
                await db.commit()
            
            cursor = await db.execute("SELECT * FROM couples WHERE id = ?", (couple["id"],))
            couple = await cursor.fetchone()
            
            if req.round == 1 and couple["partner_a_round1_done"] and couple["partner_b_round1_done"] and couple["status"] == "round1":
                await db.execute("UPDATE couples SET status = 'round2' WHERE id = ?", (couple["id"],))
                await db.commit()
            elif req.round == 2 and couple["partner_a_round2_done"] and couple["partner_b_round2_done"] and couple["status"] == "round2":
                await db.execute("UPDATE couples SET status = 'done' WHERE id = ?", (couple["id"],))
                await db.commit()
                await calculate_love_score(couple["id"], db)
                
    return {"success": True}

@app.get("/api/results/{couple_id}")
async def get_results(couple_id: int):
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM couples WHERE id = ?", (couple_id,))
        couple = await cursor.fetchone()
        if not couple:
            raise HTTPException(status_code=404, detail="Couple not found")
            
        cursor = await db.execute("SELECT * FROM answers WHERE couple_id = ?", (couple_id,))
        answers = await cursor.fetchall()
        
        cursor = await db.execute("SELECT * FROM questions WHERE active = 1")
        questions = await cursor.fetchall()
        
    ans_dict = {(a["partner"], a["round"], a["question_id"]): a["selected_option"] for a in answers}
    
    breakdown = []
    for q in questions:
        q_id = q["id"]
        a_r1 = ans_dict.get(("a", 1, q_id))
        a_r2 = ans_dict.get(("a", 2, q_id))
        b_r1 = ans_dict.get(("b", 1, q_id))
        b_r2 = ans_dict.get(("b", 2, q_id))
        
        match_a_guess = (a_r2 == b_r1) if (a_r2 and b_r1) else False
        match_b_guess = (b_r2 == a_r1) if (b_r2 and a_r1) else False
        
        breakdown.append({
            "question_id": q_id,
            "text": q["text"],
            "is_bonus": q["is_bonus"],
            "a_answer": a_r1,
            "b_guess": b_r2,
            "b_guess_correct": match_b_guess,
            "b_answer": b_r1,
            "a_guess": a_r2,
            "a_guess_correct": match_a_guess
        })
        
    return {
        "couple_id": couple["id"],
        "partner_a_name": couple["partner_a_name"],
        "partner_b_name": couple["partner_b_name"],
        "love_score": couple["love_score"],
        "breakdown": breakdown
    }

@app.get("/api/leaderboard")
async def get_leaderboard():
    async with get_db() as db:
        cursor = await db.execute("SELECT id as couple_id, partner_a_name, partner_b_name, love_score, completed_at FROM couples WHERE status = 'done' ORDER BY love_score DESC")
        couples = await cursor.fetchall()
        return [dict(c) for c in couples]

@app.get("/api/host/status")
async def host_status():
    async with get_db() as db:
        cursor = await db.execute("SELECT status, COUNT(*) as count FROM couples GROUP BY status")
        counts = await cursor.fetchall()
        
        stats = {"total": 0, "pairing": 0, "round1": 0, "round2": 0, "done": 0}
        for c in counts:
            stats[c["status"]] = c["count"]
            stats["total"] += c["count"]
            
        cursor = await db.execute("SELECT * FROM couples ORDER BY created_at DESC")
        couples = await cursor.fetchall()
        
        cursor = await db.execute("SELECT * FROM questions")
        questions = await cursor.fetchall()
        
        return {
            "stats": stats,
            "couples": [dict(c) for c in couples],
            "questions": [dict(q) for q in questions]
        }

@app.post("/api/host/reset/{couple_id}")
async def reset_couple(couple_id: int):
    async with get_db() as db:
        await db.execute('''
            UPDATE couples SET 
                status = 'round1', 
                partner_a_round1_done = 0, 
                partner_b_round1_done = 0,
                partner_a_round2_done = 0,
                partner_b_round2_done = 0,
                love_score = NULL,
                completed_at = NULL
            WHERE id = ?
        ''', (couple_id,))
        await db.execute("DELETE FROM answers WHERE couple_id = ?", (couple_id,))
        await db.commit()
    return {"success": True}

@app.post("/api/host/toggle-question/{question_id}")
async def toggle_question(question_id: int):
    async with get_db() as db:
        cursor = await db.execute("SELECT active FROM questions WHERE id = ?", (question_id,))
        row = await cursor.fetchone()
        if row:
            new_val = 0 if row["active"] else 1
            await db.execute("UPDATE questions SET active = ? WHERE id = ?", (new_val, question_id))
            await db.commit()
    return {"success": True}
