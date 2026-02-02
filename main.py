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
    # The "Hammer": Deletes the old table so the new AI columns can be created
    cur.execute("DROP TABLE IF EXISTS seats CASCADE;")
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
    yield

app = FastAPI(title="AI Booking Engine")

@app.get("/seats")
def get_seats():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM seats ORDER BY id;")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

@app.post("/book/{seat_id}")
def book_seat(seat_id: int, user_id: int, review: str):
    analysis = TextBlob(review)
    score = analysis.sentiment.polarity
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE seats 
            SET status = 'booked', user_id = %s, user_review = %s, sentiment_score = %s 
            WHERE id = %s;
        """, (user_id, review, score, seat_id))
        conn.commit()
        return {"status": "success", "ai_score": score}
    except Exception as e:
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()
