import os
import psycopg2
import nltk
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from psycopg2.extras import RealDictCursor
from contextlib import asynccontextmanager
from pydantic import BaseModel
from textblob import TextBlob

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        nltk.download('punkt', quiet=True)
        nltk.download('brown', quiet=True)
    except:
        pass
    
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
    title="AI-Powered Booking System",
    description="Seat booking with sentiment analysis and race condition prevention",
    version="1.0.0",
    lifespan=lifespan
)

class BookingRequest(BaseModel):
    user_id: int
    review: str

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Booking System</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container {
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            }
            h1 {
                color: #667eea;
                text-align: center;
            }
            .feature {
                background: #f8f9fa;
                padding: 15px;
                margin: 15px 0;
                border-left: 4px solid #667eea;
                border-radius: 5px;
            }
            .btn {
                display: block;
                background: #667eea;
                color: white;
                padding: 15px;
                text-align: center;
                text-decoration: none;
                border-radius: 8px;
                margin-top: 20px;
                font-weight: bold;
            }
            .btn:hover {
                background: #764ba2;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎫 AI-Powered Booking System</h1>
            
            <div class="feature">
                <h3>✅ Race Condition Prevention</h3>
                <p>Handles 500 simultaneous bookings - only first person gets the seat!</p>
            </div>
            
            <div class="feature">
                <h3>🤖 AI Sentiment Analysis</h3>
                <p>Automatically analyzes if reviews are positive, negative, or neutral</p>
            </div>
            
            <div class="feature">
                <h3>📊 Real-time Scoring</h3>
                <p>Uses TextBlob NLP to calculate sentiment scores (-1 to +1)</p>
            </div>
            
            <a href="/docs" class="btn">📖 Try the API Now</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/seats")
def get_seats():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT * FROM seats ORDER BY seat_number;")
    seats = cur.fetchall()
    
    available = sum(1 for s in seats if s['status'] == 'available')
    booked = len(seats) - available
    
    cur.close()
    conn.close()
    
    return {
        "total_seats": len(seats),
        "available": available,
        "booked": booked,
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
            raise HTTPException(status_code=404, detail="Seat not found")
        
        if row[0] != 'available':
            conn.rollback()
            return {
                "status": "failed",
                "message": "Seat already booked"
            }
        
        blob = TextBlob(booking.review)
        score = blob.sentiment.polarity
        
        if score > 0.1:
            label = "positive"
        elif score < -0.1:
            label = "negative"
        else:
            label = "neutral"
        
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
            "message": "Seat booked successfully!",
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
            COUNT(*) FILTER (WHERE sentiment_label = 'positive') as positive_reviews,
            COUNT(*) FILTER (WHERE sentiment_label = 'negative') as negative_reviews,
            COUNT(*) FILTER (WHERE sentiment_label = 'neutral') as neutral_reviews,
            AVG(sentiment_score) as average_score
        FROM seats
        WHERE user_review IS NOT NULL;
    """)
    
    stats = cur.fetchone()
    
    cur.execute("""
        SELECT seat_number, user_id, user_review, sentiment_score, sentiment_label
        FROM seats
        WHERE user_review IS NOT NULL
        ORDER BY id;
    """)
    
    reviews = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return {
        "statistics": stats,
        "all_reviews": reviews
    }
