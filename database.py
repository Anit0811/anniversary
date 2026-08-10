import aiosqlite
import os
from contextlib import asynccontextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'love_quiz.db')

@asynccontextmanager
async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()

async def init_db():
    async with get_db() as db:
        await db.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            genre TEXT,
            text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            is_bonus BOOLEAN DEFAULT 0,
            active BOOLEAN DEFAULT 1
        )
        ''')

        await db.execute('''
        CREATE TABLE IF NOT EXISTS couples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code TEXT UNIQUE NOT NULL,
            partner_a_name TEXT NOT NULL,
            partner_b_name TEXT,
            partner_a_token TEXT UNIQUE NOT NULL,
            partner_b_token TEXT UNIQUE,
            status TEXT DEFAULT 'pairing',
            partner_a_round1_done BOOLEAN DEFAULT 0,
            partner_b_round1_done BOOLEAN DEFAULT 0,
            partner_a_round2_done BOOLEAN DEFAULT 0,
            partner_b_round2_done BOOLEAN DEFAULT 0,
            love_score REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
        ''')

        await db.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            couple_id INTEGER NOT NULL,
            partner TEXT NOT NULL,
            question_id INTEGER NOT NULL,
            round INTEGER NOT NULL,
            selected_option TEXT NOT NULL,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (couple_id) REFERENCES couples(id),
            FOREIGN KEY (question_id) REFERENCES questions(id),
            UNIQUE(couple_id, partner, question_id, round)
        )
        ''')
        await db.commit()

async def seed_questions():
    async with get_db() as db:
        cursor = await db.execute('SELECT COUNT(*) as count FROM questions')
        row = await cursor.fetchone()
        if row and row['count'] > 0:
            return  # Already seeded
                
        questions = [
            ("Habits", "What is my absolute favorite way to spend a lazy Sunday?", "Sleeping till noon", "Binge-watching a series", "Trying out a new cafe", "Spring cleaning the house", False),
            ("Memories", "Where did we have our very first date?", "Coffee shop", "Movie theater", "Restaurant", "Park/Outdoor", False),
            ("Preferences", "If I had to eat one cuisine for the rest of my life, what would it be?", "North Indian/Punjabi", "South Indian", "Italian (Pizza/Pasta)", "Chinese/Asian", False),
            ("Habits", "What is my worst habit according to you?", "Leaving wet towels on the bed", "Being constantly on the phone", "Taking too long to get ready", "Snoring/Stealing blankets", False),
            ("Love", "What was my first impression of you?", "You were too talkative", "You were incredibly sweet", "You seemed arrogant", "I was instantly intimidated by you", False),
            ("Memories", "Which trip of ours is my absolute favorite?", "Our honeymoon", "That spontaneous weekend getaway", "Our first trip with friends", "A peaceful hill station trip", False),
            ("Preferences", "What is my go-to comfort food when I'm stressed?", "Maggi", "Ice cream/Chocolates", "Biryani", "Chaat/Pani Puri", False),
            ("Habits", "How do I typically handle arguments?", "I need space immediately", "I want to talk it out right away", "I give the silent treatment", "I apologize first to end it", False),
            ("Love", "What do I love most about you?", "Your sense of humor", "Your caring nature", "Your ambition", "Your cooking/food choices", False),
            ("Preferences", "If we won the lottery tomorrow, what's the first thing I would buy?", "A luxury car", "A massive house", "Tickets for a world tour", "Invest it all smartly", False),
            ("Habits", "What is my role when we are packing for a trip?", "The over-packer who takes everything", "The one who forgets essentials", "The organized one with a list", "The one who packs 1 hour before", False),
            ("Memories", "What is my favorite gift that you have ever given me?", "A piece of jewelry/watch", "A thoughtful handmade gift", "A surprise trip/experience", "A gadget I really wanted", False),
            ("Preferences", "What movie genre do I actually prefer, even if I pretend otherwise?", "Rom-Coms", "Action/Thriller", "Horror", "Documentaries", False),
            ("Habits", "Who takes longer to get ready for a party?", "Definitely me", "Definitely you", "We both take forever", "We are always magically on time", False),
            ("Love", "What is my idea of a perfect romantic evening?", "Fancy dinner date", "Cozy movie night at home", "Long drive with music", "Cooking together with wine", False)
        ]

        for q in questions:
            await db.execute('''
                INSERT INTO questions (genre, text, option_a, option_b, option_c, option_d, is_bonus)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', q)
            
        await db.commit()
