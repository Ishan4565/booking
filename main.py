import os
import psycopg2
import nltk
from fastapi import FastAPI
from psycopg2.extras import RealDictCursor
from contextlib import asynccontextmanager
from textblob import TextBlob

nltk.download('punkt_tab')
DATABASE_URL = os.environ.get("DATABASE_URL")

@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS seats CASCADE;")
    cur.execute("""
        CREATE TABLE seats (
            id SERIAL PRIMARY KEY,
            seat_number VARCHAR(10) UNIQUE NOT NULL,
            status VARCHAR(20) DEFAULT 'available',
            user_id INTEGER,
            review_sound TEXT,
            review_seat TEXT,
            review_service TEXT,
            avg_sentiment FLOAT
        );
    """)
    seats = [(f'A{i}',) for i in range(1, 11)]
    cur.executemany("INSERT INTO seats (seat_number) VALUES (%s);", seats)
    conn.commit()
    cur.close()
    conn.close()
    yield

app = FastAPI(title="Pro Reviewer Engine")

@app.post("/book/{seat_id}")
def book_seat(seat_id: int, user_id: int, sound_review: str, seat_review: str, service_review: str):
    # Calculate sentiment for each category
    s1 = TextBlob(sound_review).sentiment.polarity
    s2 = TextBlob(seat_review).sentiment.polarity
    s3 = TextBlob(service_review).sentiment.polarity
    
    # Calculate overall experience score
    total_avg = (s1 + s2 + s3) / 3

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE seats 
            SET status = 'booked', 
                user_id = %s, 
                review_sound = %s, 
                review_seat = %s, 
                review_service = %s,
                avg_sentiment = %s 
            WHERE id = %s;
        """, (user_id, sound_review, seat_review, service_review, total_avg, seat_id))
        conn.commit()
        return {
            "status": "Success",
            "overall_happiness_score": round(total_avg, 2),
            "summary": "Reviews stored for Sound, Seating, and Service."
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()

@app.get("/seats")
def get_seats():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM seats ORDER BY id;")
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data
