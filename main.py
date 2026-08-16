from fastapi import FastAPI, Request, Form, Response, Cookie, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import database as db
import uvicorn
from typing import Optional

app = FastAPI(title="Love Quiz")

# Setup static and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def startup():
    db.init_db()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, couple_id: Optional[str] = Cookie(None), partner: Optional[str] = Cookie(None)):
    if couple_id and partner:
        # Check if they should be redirected to their current round
        couple = db.get_couple(int(couple_id))
        if couple:
            return RedirectResponse(url="/quiz")
            
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/start")
async def start_couple(request: Request, partner_a_name: str = Form(...)):
    couple_id, code = db.create_couple(partner_a_name)
    response = RedirectResponse(url=f"/waiting?code={code}", status_code=302)
    response.set_cookie(key="couple_id", value=str(couple_id))
    response.set_cookie(key="partner", value="a")
    return response

@app.post("/join")
async def join_couple_post(request: Request, room_code: str = Form(...), partner_b_name: str = Form(...)):
    room_code = room_code.strip().upper()
    couple_id = db.join_couple(room_code, partner_b_name)
    if not couple_id:
        # We could return a JSON error, but simple redirect with query for now
        return RedirectResponse(url="/?error=invalid_code", status_code=302)
        
    response = RedirectResponse(url="/quiz", status_code=302)
    response.set_cookie(key="couple_id", value=str(couple_id))
    response.set_cookie(key="partner", value="b")
    return response

@app.get("/waiting", response_class=HTMLResponse)
async def waiting(request: Request, code: str):
    return templates.TemplateResponse("waiting_room.html", {"request": request, "code": code})

@app.get("/quiz", response_class=HTMLResponse)
async def quiz(request: Request, q: Optional[int] = None, couple_id: Optional[str] = Cookie(None), partner: Optional[str] = Cookie(None)):
    if not couple_id or not partner:
        return RedirectResponse(url="/")
        
    couple = db.get_couple(int(couple_id))
    if not couple:
        response = RedirectResponse(url="/")
        response.delete_cookie("couple_id")
        response.delete_cookie("partner")
        return response
        
    if couple['status'] == 'pairing':
        return RedirectResponse(url=f"/waiting?code={couple['room_code']}")
        
    if couple['status'] == 'done' and q is None:
        return RedirectResponse(url="/results")
        
    round_num = 1 if couple['status'] in ['round1', 'done'] else 2
    if couple['status'] == 'done':
        # If they are done but navigating back, keep them in round 2
        round_num = 2
        
    # Get questions
    questions = db.get_couple_questions(int(couple_id), partner, round_num)
    
    # Get answered questions for this partner and round
    answered = db.get_answered_questions(int(couple_id), partner, round_num)
    
    if q is not None and 1 <= q <= len(questions):
        q_index = q - 1
        current_q = questions[q_index]
    else:
        # Find next unanswered question
        next_q = None
        q_index = 0
        for i, question in enumerate(questions):
            if question['id'] not in answered:
                next_q = question
                q_index = i
                break
                
        if not next_q:
            # This partner finished the round, check if other did
            if couple['status'] == 'done':
                return RedirectResponse(url="/results")
            return templates.TemplateResponse("waiting_partner.html", {"request": request})
            
        current_q = next_q
        
    has_previous = q_index > 0
    has_next = current_q['id'] in answered and q_index < len(questions) - 1
        
    # the question text changes in round 2
    if round_num == 2:
        other_name = couple['partner_b_name'] if partner == 'a' else couple['partner_a_name']
        prompt = f"What do you think {other_name} answered?"
    else:
        prompt = "Answer about yourself"
        
    current_selected = answered.get(current_q['id'])
        
    return templates.TemplateResponse("quiz.html", {
        "request": request,
        "question": current_q,
        "q_index": q_index + 1,
        "total_q": len(questions),
        "round_num": round_num,
        "prompt": prompt,
        "has_previous": has_previous,
        "has_next": has_next,
        "current_selected": current_selected
    })

@app.post("/answer")
async def submit_answer(
    request: Request, 
    question_id: int = Form(...), 
    selected_option: str = Form(...),
    round_num: int = Form(...),
    q_index: int = Form(...),
    couple_id: Optional[str] = Cookie(None), 
    partner: Optional[str] = Cookie(None)
):
    if not couple_id or not partner:
        return RedirectResponse(url="/", status_code=302)
        
    db.save_answer(int(couple_id), partner, question_id, round_num, selected_option)
    status = db.check_round_completion(int(couple_id))
    
    if status in ['round2', 'done'] and round_num == (1 if status == 'round2' else 2):
        # Round just finished, check if they were on the last question of the round
        return RedirectResponse(url="/quiz", status_code=302)
    
    return RedirectResponse(url=f"/quiz?q={q_index + 1}", status_code=302)

@app.get("/api/status")
async def get_status(couple_id: Optional[str] = Cookie(None)):
    if not couple_id:
        return {"status": "error"}
        
    couple = db.get_couple(int(couple_id))
    if not couple:
        return {"status": "error"}
        
    return {"status": couple['status']}

@app.get("/results", response_class=HTMLResponse)
async def results(request: Request, couple_id: Optional[str] = Cookie(None), partner: Optional[str] = Cookie(None)):
    if not couple_id or not partner:
        return RedirectResponse(url="/")
        
    couple = db.get_couple(int(couple_id))
    if couple['status'] != 'done':
        return RedirectResponse(url="/quiz")
        
    results_data = db.get_couple_results(int(couple_id), partner)
        
    return templates.TemplateResponse("results.html", {
        "request": request,
        "couple": couple,
        "partner": partner,
        "my_guesses": results_data['my_guesses'],
        "their_guesses": results_data['their_guesses']
    })

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard(request: Request):
    return templates.TemplateResponse("leaderboard.html", {"request": request})

@app.get("/api/leaderboard")
async def api_leaderboard():
    couples = db.get_leaderboard()
    return {"couples": couples}

@app.get("/host-xyz123", response_class=HTMLResponse)
async def host_panel(request: Request):
    couples = db.get_all_couples()
    return templates.TemplateResponse("host.html", {"request": request, "couples": couples})

@app.post("/host-xyz123/delete/{couple_id}")
async def host_delete_couple(couple_id: int):
    db.delete_couple(couple_id)
    return RedirectResponse(url="/host-xyz123", status_code=302)

@app.get("/retake")
async def retake(request: Request):
    response = RedirectResponse(url="/")
    response.delete_cookie("couple_id")
    response.delete_cookie("partner")
    return response

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
