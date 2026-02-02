import os
import psycopg2
from fastapi import FastAPI, HTTPException
from psycopg2.extras import RealDictCursor
from contextlib import asynccontextmanager
from pydantic import BaseModel

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except:
    TEXTBLOB_AVAILABLE = False

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is required")

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
            user_review TEXT,
            sentiment_score FLOAT,
            sentiment_label VARCHAR(20)
        );
    """)
    
    seats = [(f'A{i}',) for i in range(1, 21)]
    cur.executemany("INSERT INTO seats (seat_number) VALUES (%s);", seats)
    
    conn.commit()
    cur.close()
    conn.close()
    
    yield

app = FastAPI(
    title="Booking System with AI",
    lifespan=lifespan
)

class BookingRequest(BaseModel):
    user_id: int
    review: str

def analyze_sentiment(text):
    if not TEXTBLOB_AVAILABLE:
        return 0.0, "neutral"
    
    try:
        blob = TextBlob(text)
        score = blob.sentiment.polarity
        
        if score > 0.1:
            label = "positive"
        elif score < -0.1:
            label = "negative"
        else:
            label = "neutral"
        
        return score, label
    except:
        return 0.0, "neutral"

@app.get("/seats")
def get_seats():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT * FROM seats ORDER BY seat_number;")
    seats = cur.fetchall()
    
    available = sum(1 for s in seats if s['status'] == 'available')
    
    cur.close()
    conn.close()
    
    return {
        "total_seats": len(seats),
        "available": available,
        "booked": len(seats) - available,
        "seats": seats
    }

@app.post("/book/{seat_id}")
def book_seat(seat_id: int, booking: BookingRequest):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        cur.execute(
            "SELECT status FROM seats WHERE id = %s FOR UPDATE;",
            (seat_id,)
        )
        row = cur.fetchone()
        
        if not row:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Seat not found")
        
        if row[0] != 'available':
            conn.rollback()
            return {
                "status": "failed",
                "message": "Seat already booked"
            }
        
        score, label = analyze_sentiment(booking.review)
        
        cur.execute("""
            UPDATE seats 
            SET status = 'booked', 
                user_id = %s, 
                user_review = %s, 
                sentiment_score = %s,
                sentiment_label = %s
            WHERE id = %s;
        """, (booking.user_id, booking.review, score, label, seat_id))
        
        conn.commit()
        
        cur.execute(
            "SELECT seat_number FROM seats WHERE id = %s;",
            (seat_id,)
        )
        seat_number = cur.fetchone()[0]
        
        return {
            "status": "success",
            "message": "Seat booked successfully",
            "seat_number": seat_number,
            "user_id": booking.user_id,
            "review": booking.review,
            "sentiment_score": round(score, 3),
            "sentiment": label
        }
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cur.close()
        conn.close()

@app.get("/analytics")
def get_analytics():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            seat_number, 
            user_id, 
            user_review, 
            sentiment_score, 
            sentiment_label
        FROM seats
        WHERE user_review IS NOT NULL
        ORDER BY id;
    """)
    
    reviews = cur.fetchall()
    
    positive = sum(1 for r in reviews if r['sentiment_label'] == 'positive')
    negative = sum(1 for r in reviews if r['sentiment_label'] == 'negative')
    neutral = sum(1 for r in reviews if r['sentiment_label'] == 'neutral')
    
    cur.close()
    conn.close()
    
    return {
        "total_reviews": len(reviews),
        "positive": positive,
        "negative": negative,
        "neutral": neutral,
        "reviews": reviews
    }
