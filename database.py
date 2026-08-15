import sqlite3
import random
import string
import json
from datetime import datetime

DB_PATH = "love_quiz.db"

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY,
            text TEXT,
            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            active BOOLEAN DEFAULT 1
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS couples (
            id INTEGER PRIMARY KEY,
            room_code TEXT UNIQUE,
            partner_a_name TEXT,
            partner_b_name TEXT,
            status TEXT,
            love_score REAL,
            created_at TIMESTAMP,
            completed_at TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY,
            couple_id INTEGER,
            partner TEXT,
            question_id INTEGER,
            round INTEGER,
            selected_option TEXT,
            answered_at TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS couple_questions (
            id INTEGER PRIMARY KEY,
            couple_id INTEGER,
            partner TEXT,
            question_order TEXT
        )
    ''')
    
    c.execute('SELECT COUNT(*) FROM questions')
    if c.fetchone()[0] == 0:
        seed_questions(conn)
        
    conn.commit()
    conn.close()

def seed_questions(conn):
    questions = [
        ("Your idea of a perfect lazy Sunday is...", "Sleeping in till noon", "Long breakfast + phone in bed", "Movie marathon", '"Relaxing" but somehow still doing chores'),
        ("If you had to eat just ONE dish for the rest of your life, it'd be...", "Something spicy & desi", "Something sweet", "A comfort classic like dal-chawal/khichdi", "You could never choose just one"),
        ("Your biggest guilty habit is...", "Losing your phone/keys constantly", "Snoring or talking in your sleep", "Leaving lights/fans on everywhere", "Being chronically late"),
        ("You just won the lottery — first thing you're buying is...", "A house/property", "A car", "A big trip", "Something for the family"),
        ("When packing for a trip, you're the one who...", "Packs days in advance with a list", "Throws it all in last minute", 'Over-packs "just in case"', "Makes everyone else pack while you supervise"),
        ("The kind of movie that always makes you stop and watch, no matter how many times you've seen it, is...", "A romantic drama", "A comedy", "An action-thriller", "An old family classic"),
        ("The kind of song that makes you turn the volume up is...", "An old-school classic", "A soft romantic melody", "An upbeat dance number", "A soulful/devotional tune"),
        ("Your idea of the perfect romantic evening is...", "A quiet dinner at home", "A fancy night out", "A long walk and talk", "Just watching something together"),
        ("Your dream trip right now is...", "A mountain getaway", "A beach holiday", "A pilgrimage", "Somewhere abroad you've never been"),
        ("On a holiday, by evening you're usually...", "Ready to crash early", "Still up for going out", "Looking for good food nearby", "Wanting one more thing ticked off the list"),
        ("The shades you're naturally drawn to are...", "Soft pastels", "Deep, bold colours", "Classic black & white/neutrals", "Bright, vibrant colours"),
        ("If you suddenly got a totally free evening tonight, you'd...", "Call up a friend", "Curl up with a book/music, alone", "Cook something just for the joy of it", "Go for a drive/walk with no destination"),
        ("When you're stressed, your go-to move is...", "Eating something", "Talking to someone about it", "Sleeping it off", "Cleaning or organizing something"),
        ("If you could instantly master one skill, it'd be...", "Cooking", "Dancing", "A musical instrument", "Public speaking"),
        ("Your idea of the perfect gift to receive is...", "Something handmade or personal", "Something practical you actually need", "Something surprising and spontaneous", "An experience, not a thing"),
        ("Left alone at a grocery store, you always end up buying...", "Snacks you didn't plan for", "Way more than the list", "Exactly what's on the list, nothing else", "Something for someone else, not yourself"),
        ("Your favourite kind of weather is...", "Monsoon rain", "Crisp winter cold", "Warm sunny days", "Cool breezy evenings"),
        ("When it comes to sleep, you're...", "Asleep the moment your head hits the pillow", "Someone who needs total silence and dark", "A light sleeper, up at every sound", "Someone who reads/scrolls till you doze off"),
        ("At a big family function, you're usually the one...", "On the dance floor first", "Chatting in a corner with a few people", "Helping host/organize things", "Sneaking off early"),
        ("When you need to unwind after a long day, you reach for...", "Food", "Music or a show", "A phone call to someone", "Silence and some time alone"),
        ("When it comes to spending money, you're more of a...", "A planner — budgets everything", "A spontaneous spender", "A saver, thinks twice always", "Spends freely on others, careful for yourself"),
        ("The very first thing you do after waking up is...", "Check your phone", "Make tea/coffee", "Step outside or open a window", "Lie there a few minutes before moving")
    ]
    
    c = conn.cursor()
    for q in questions:
        c.execute('''
            INSERT INTO questions (text, option_a, option_b, option_c, option_d, active)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', q)

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def create_couple(partner_a_name):
    conn = get_db()
    c = conn.cursor()
    while True:
        code = generate_room_code()
        c.execute("SELECT id FROM couples WHERE room_code = ?", (code,))
        if not c.fetchone():
            break
    
    c.execute('''
        INSERT INTO couples (room_code, partner_a_name, status, created_at)
        VALUES (?, ?, 'pairing', ?)
    ''', (code, partner_a_name, datetime.now()))
    
    couple_id = c.lastrowid
    conn.commit()
    conn.close()
    return couple_id, code

def join_couple(room_code, partner_b_name):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM couples WHERE room_code = ? AND status = 'pairing'", (room_code,))
    couple = c.fetchone()
    
    if not couple:
        conn.close()
        return None
        
    couple_id = couple['id']
    c.execute('''
        UPDATE couples 
        SET partner_b_name = ?, status = 'round1' 
        WHERE id = ?
    ''', (partner_b_name, couple_id))
    
    # Generate 15 random questions per partner
    c.execute("SELECT id FROM questions WHERE active = 1")
    all_q_ids = [row['id'] for row in c.fetchall()]
    num_questions = min(15, len(all_q_ids))
    
    a_q_ids = random.sample(all_q_ids, num_questions)
    b_q_ids = random.sample(all_q_ids, num_questions)
    
    c.execute('''
        INSERT INTO couple_questions (couple_id, partner, question_order)
        VALUES (?, 'a', ?)
    ''', (couple_id, json.dumps(a_q_ids)))
    
    c.execute('''
        INSERT INTO couple_questions (couple_id, partner, question_order)
        VALUES (?, 'b', ?)
    ''', (couple_id, json.dumps(b_q_ids)))
    
    conn.commit()
    conn.close()
    return couple_id

def get_couple(couple_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM couples WHERE id = ?", (couple_id,))
    res = c.fetchone()
    conn.close()
    return dict(res) if res else None

def get_couple_questions(couple_id, partner, round_num):
    target_partner = partner if round_num == 1 else ('b' if partner == 'a' else 'a')
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT question_order FROM couple_questions WHERE couple_id = ? AND partner = ?", (couple_id, target_partner))
    row = c.fetchone()
    if not row:
        conn.close()
        return []
    
    q_ids = json.loads(row['question_order'])
    
    questions = []
    for q_id in q_ids:
        c.execute("SELECT * FROM questions WHERE id = ?", (q_id,))
        q = c.fetchone()
        if q:
            questions.append(dict(q))
    
    conn.close()
    return questions

def save_answer(couple_id, partner, question_id, round_num, selected_option):
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT id FROM answers 
        WHERE couple_id = ? AND partner = ? AND question_id = ? AND round = ?
    ''', (couple_id, partner, question_id, round_num))
    
    if not c.fetchone():
        c.execute('''
            INSERT INTO answers (couple_id, partner, question_id, round, selected_option, answered_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (couple_id, partner, question_id, round_num, selected_option, datetime.now()))
        conn.commit()
    conn.close()

def get_answered_questions(couple_id, partner, round_num):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT question_id, selected_option FROM answers 
        WHERE couple_id = ? AND partner = ? AND round = ?
    ''', (couple_id, partner, round_num))
    res = {row['question_id']: row['selected_option'] for row in c.fetchall()}
    conn.close()
    return res

def get_all_answered_count(couple_id, partner, round_num):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT COUNT(*) FROM answers 
        WHERE couple_id = ? AND partner = ? AND round = ?
    ''', (couple_id, partner, round_num))
    count = c.fetchone()[0]
    conn.close()
    return count

def check_round_completion(couple_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT status FROM couples WHERE id = ?", (couple_id,))
    status = c.fetchone()['status']
    
    c.execute("SELECT question_order FROM couple_questions WHERE couple_id = ? AND partner = 'a'", (couple_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return status
        
    num_questions = len(json.loads(row['question_order']))
    
    # Get counts for A and B in round 1
    c.execute("SELECT COUNT(*) FROM answers WHERE couple_id = ? AND partner = 'a' AND round = 1", (couple_id,))
    a_round1 = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM answers WHERE couple_id = ? AND partner = 'b' AND round = 1", (couple_id,))
    b_round1 = c.fetchone()[0]
    
    if status == 'round1' and a_round1 >= num_questions and b_round1 >= num_questions:
        c.execute("UPDATE couples SET status = 'round2' WHERE id = ?", (couple_id,))
        status = 'round2'
        
    # Get counts for A and B in round 2
    if status == 'round2':
        c.execute("SELECT COUNT(*) FROM answers WHERE couple_id = ? AND partner = 'a' AND round = 2", (couple_id,))
        a_round2 = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM answers WHERE couple_id = ? AND partner = 'b' AND round = 2", (couple_id,))
        b_round2 = c.fetchone()[0]
        
        if a_round2 >= num_questions and b_round2 >= num_questions:
            status = 'done'
            c.execute("UPDATE couples SET status = 'done', completed_at = ? WHERE id = ?", (datetime.now(), couple_id))
            
            # calculate score
            c.execute("SELECT question_id, selected_option FROM answers WHERE couple_id = ? AND partner = 'a' AND round = 1", (couple_id,))
            a_actual = {row['question_id']: row['selected_option'] for row in c.fetchall()}
            
            c.execute("SELECT question_id, selected_option FROM answers WHERE couple_id = ? AND partner = 'b' AND round = 1", (couple_id,))
            b_actual = {row['question_id']: row['selected_option'] for row in c.fetchall()}
            
            c.execute("SELECT question_id, selected_option FROM answers WHERE couple_id = ? AND partner = 'a' AND round = 2", (couple_id,))
            a_guess = {row['question_id']: row['selected_option'] for row in c.fetchall()}
            
            c.execute("SELECT question_id, selected_option FROM answers WHERE couple_id = ? AND partner = 'b' AND round = 2", (couple_id,))
            b_guess = {row['question_id']: row['selected_option'] for row in c.fetchall()}
            
            matches = 0
            total_possible = num_questions * 2
            
            for q_id in a_guess:
                if a_guess.get(q_id) == b_actual.get(q_id):
                    matches += 1
            for q_id in b_guess:
                if b_guess.get(q_id) == a_actual.get(q_id):
                    matches += 1
            
            score = (matches / total_possible) * 100 if total_possible > 0 else 0
            c.execute("UPDATE couples SET love_score = ? WHERE id = ?", (score, couple_id))

    conn.commit()
    conn.close()
    return status

def get_couple_results(couple_id, partner):
    conn = get_db()
    c = conn.cursor()
    
    my_target = 'b' if partner == 'a' else 'a'
    
    c.execute("SELECT question_order FROM couple_questions WHERE couple_id = ? AND partner = ?", (couple_id, my_target))
    my_guesses_q_ids = json.loads(c.fetchone()['question_order'])
    
    c.execute("SELECT question_order FROM couple_questions WHERE couple_id = ? AND partner = ?", (couple_id, partner))
    their_guesses_q_ids = json.loads(c.fetchone()['question_order'])
    
    c.execute("SELECT id, text FROM questions")
    q_dict = {row['id']: row['text'] for row in c.fetchall()}
    
    c.execute("SELECT question_id, selected_option FROM answers WHERE couple_id = ? AND partner = 'a' AND round = 1", (couple_id,))
    a_actual = {row['question_id']: row['selected_option'] for row in c.fetchall()}
    c.execute("SELECT question_id, selected_option FROM answers WHERE couple_id = ? AND partner = 'b' AND round = 1", (couple_id,))
    b_actual = {row['question_id']: row['selected_option'] for row in c.fetchall()}
    
    c.execute("SELECT question_id, selected_option FROM answers WHERE couple_id = ? AND partner = 'a' AND round = 2", (couple_id,))
    a_guess = {row['question_id']: row['selected_option'] for row in c.fetchall()}
    c.execute("SELECT question_id, selected_option FROM answers WHERE couple_id = ? AND partner = 'b' AND round = 2", (couple_id,))
    b_guess = {row['question_id']: row['selected_option'] for row in c.fetchall()}
    
    conn.close()
    
    my_guesses_results = []
    for q_id in my_guesses_q_ids:
        q_text = q_dict.get(q_id)
        if partner == 'a':
            matched = a_guess.get(q_id) == b_actual.get(q_id)
        else:
            matched = b_guess.get(q_id) == a_actual.get(q_id)
        my_guesses_results.append({'question': q_text, 'matched': matched})
        
    their_guesses_results = []
    for q_id in their_guesses_q_ids:
        q_text = q_dict.get(q_id)
        if partner == 'a':
            matched = b_guess.get(q_id) == a_actual.get(q_id)
        else:
            matched = a_guess.get(q_id) == b_actual.get(q_id)
        their_guesses_results.append({'question': q_text, 'matched': matched})

    return {
        'my_guesses': my_guesses_results,
        'their_guesses': their_guesses_results
    }

def get_leaderboard():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT id, partner_a_name, partner_b_name, love_score, status 
        FROM couples 
        WHERE status = 'done'
        ORDER BY love_score DESC, completed_at ASC
    ''')
    res = [dict(row) for row in c.fetchall()]
    conn.close()
    return res

def get_all_couples():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT id, room_code, partner_a_name, partner_b_name, status, love_score 
        FROM couples 
        ORDER BY id DESC
    ''')
    res = [dict(row) for row in c.fetchall()]
    conn.close()
    return res

def delete_couple(couple_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM answers WHERE couple_id = ?", (couple_id,))
    c.execute("DELETE FROM couple_questions WHERE couple_id = ?", (couple_id,))
    c.execute("DELETE FROM couples WHERE id = ?", (couple_id,))
    conn.commit()
    conn.close()
