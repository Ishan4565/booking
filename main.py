import os
import psycopg2
from fastapi import FastAPI
from psycopg2.extras import RealDictCursor
from contextlib import asynccontextmanager
from textblob import TextBlob

DATABASE_URL = os.environ.get("DATABASE_URL")

@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS seats (
            id SERIAL PRIMARY KEY,
            seat_number VARCHAR(10) UNIQUE NOT NULL,
            status VARCHAR(20) DEFAULT 'available',
            user_id INTEGER,
            user_review TEXT,
            sentiment_score FLOAT
        );
    """)
    cur.execute("SELECT count(*) FROM seats;")
    if cur.fetchone()[0] == 0:
        seats = [(f'A{i}',) for i in range(1, 11)]
        cur.executemany("INSERT INTO seats (seat_number) VALUES (%s);", seats)
    conn.commit()
    cur.close()
    conn.close()
    yield

app = FastAPI(title="Lightweight AI Booking Engine", lifespan=lifespan)

@app.get("/seats", tags=["Dashboard"])
def get_seats():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM seats ORDER BY id;")
    seats = cur.fetchall()
    cur.close()
    conn.close()
    return seats

@app.post("/book/{seat_id}", tags=["Booking"])
def book_seat(seat_id: int, user_id: int, review: str):
    analysis = TextBlob(review)
    score = analysis.sentiment.polarity
    
    label = "POSITIVE" if score > 0 else "NEGATIVE" if score < 0 else "NEUTRAL"

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    try:
        cur.execute("SELECT status FROM seats WHERE id = %s FOR UPDATE;", (seat_id,))
        row = cur.fetchone()
        
        if not row:
            return {"error": "Seat not found"}
            
        if row[0] == 'available':
            cur.execute("""
                UPDATE seats 
                SET status = 'booked', user_id = %s, user_review = %s, sentiment_score = %s 
                WHERE id = %s;
            """, (user_id, review, score, seat_id))
            conn.commit()
            return {
                "message": f"Success! Seat {seat_id} booked.",
                "ai_feedback": f"Sentiment detected: {label} (Score: {score:.2f})"
            }
        return {"message": "Seat already taken"}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()

@app.post("/reset", tags=["Admin"])
def reset_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    # This line forces the database to delete the old structure
    cur.execute("DROP TABLE IF EXISTS seats CASCADE;")
    # This part builds the NEW structure with AI columns
    cur.execute("""
        CREATE TABLE seats (
            id SERIAL PRIMARY KEY,
            seat_number VARCHAR(10) UNIQUE NOT NULL,
            status VARCHAR(20) DEFAULT 'available',
            user_id INTEGER,
            user_review TEXT,
            sentiment_score FLOAT
        );
    """)
    
    seats = [(f'A{i}',) for i in range(1, 11)]
    cur.executemany("INSERT INTO seats (seat_number) VALUES (%s);", seats)
    conn.commit()
    cur.close()
    conn.close()
    return {"message": "Database REBUILT with AI columns. Try booking now!"}
