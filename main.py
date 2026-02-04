import os
import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from psycopg2.extras import RealDictCursor
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

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
    
    cur.execute("DROP TABLE IF EXISTS reviews CASCADE;")
    cur.execute("DROP TABLE IF EXISTS seats CASCADE;")
    
    cur.execute("""
        CREATE TABLE seats (
            id SERIAL PRIMARY KEY,
            seat_number VARCHAR(10) UNIQUE NOT NULL,
            status VARCHAR(20) DEFAULT 'available',
            user_id INTEGER,
            user_name VARCHAR(100),
            booked_at TIMESTAMP
        );
    """)
    
    cur.execute("""
        CREATE TABLE reviews (
            review_id SERIAL PRIMARY KEY,
            seat_id INTEGER REFERENCES seats(id),
            user_id INTEGER NOT NULL,
            user_name VARCHAR(100),
            
            overall_experience TEXT,
            overall_sentiment_score FLOAT,
            overall_sentiment_label VARCHAR(20),
            
            sound_quality_review TEXT,
            sound_quality_score FLOAT,
            sound_quality_label VARCHAR(20),
            
            seat_comfort_review TEXT,
            seat_comfort_score FLOAT,
            seat_comfort_label VARCHAR(20),
            
            seat_height_review TEXT,
            seat_height_score FLOAT,
            seat_height_label VARCHAR(20),
            
            view_quality_review TEXT,
            view_quality_score FLOAT,
            view_quality_label VARCHAR(20),
            
            booking_service_review TEXT,
            booking_service_score FLOAT,
            booking_service_label VARCHAR(20),
            
            staff_behavior_review TEXT,
            staff_behavior_score FLOAT,
            staff_behavior_label VARCHAR(20),
            
            cleanliness_review TEXT,
            cleanliness_score FLOAT,
            cleanliness_label VARCHAR(20),
            
            value_for_money_review TEXT,
            value_for_money_score FLOAT,
            value_for_money_label VARCHAR(20),
            
            average_score FLOAT,
            overall_rating VARCHAR(20),
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    seats = [(f'A{i}',) for i in range(1, 11)] + [(f'B{i}',) for i in range(1, 11)] + [(f'C{i}',) for i in range(1, 11)]
    cur.executemany("INSERT INTO seats (seat_number) VALUES (%s);", seats)
    
    conn.commit()
    cur.close()
    conn.close()
    
    yield

app = FastAPI(
    title="Advanced Booking & Review System",
    description="Seat booking with comprehensive multi-aspect review analysis",
    version="2.0.0",
    lifespan=lifespan
)

class BookingRequest(BaseModel):
    user_id: int
    user_name: str

class ReviewRequest(BaseModel):
    user_id: int
    user_name: str
    
    overall_experience: str = Field(..., description="Your overall experience")
    sound_quality_review: Optional[str] = Field(None, description="Review about sound/audio quality")
    seat_comfort_review: Optional[str] = Field(None, description="Review about seat comfort")
    seat_height_review: Optional[str] = Field(None, description="Review about seat height/position")
    view_quality_review: Optional[str] = Field(None, description="Review about view/visibility")
    booking_service_review: Optional[str] = Field(None, description="Review about booking service")
    staff_behavior_review: Optional[str] = Field(None, description="Review about staff behavior")
    cleanliness_review: Optional[str] = Field(None, description="Review about cleanliness")
    value_for_money_review: Optional[str] = Field(None, description="Review about value for money")

def analyze_sentiment(text):
    if not text or not TEXTBLOB_AVAILABLE:
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

def get_overall_rating(avg_score):
    if avg_score >= 0.6:
        return "excellent"
    elif avg_score >= 0.3:
        return "good"
    elif avg_score >= 0.0:
        return "average"
    elif avg_score >= -0.3:
        return "poor"
    else:
        return "very_poor"

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Advanced Booking System</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container {
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            h1 {
                color: #667eea;
                text-align: center;
                margin-bottom: 10px;
            }
            .subtitle {
                text-align: center;
                color: #666;
                margin-bottom: 30px;
            }
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .feature {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                border-left: 4px solid #667eea;
            }
            .feature h3 {
                color: #667eea;
                margin-top: 0;
            }
            .review-categories {
                background: #e8f4f8;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }
            .review-categories h3 {
                color: #2c5aa0;
                margin-top: 0;
            }
            .review-categories ul {
                columns: 2;
                column-gap: 30px;
            }
            .review-categories li {
                margin: 10px 0;
            }
            .btn {
                display: block;
                background: #667eea;
                color: white;
                padding: 15px;
                text-align: center;
                text-decoration: none;
                border-radius: 10px;
                font-weight: bold;
                margin-top: 20px;
            }
            .btn:hover {
                background: #764ba2;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎭 Advanced Booking & Review System</h1>
            <p class="subtitle">Complete booking solution with comprehensive multi-aspect reviews</p>
            
            <div class="features">
                <div class="feature">
                    <h3>🔒 Race Condition Prevention</h3>
                    <p>Handles 500 simultaneous bookings - only first person gets the seat!</p>
                </div>
                
                <div class="feature">
                    <h3>🤖 AI Sentiment Analysis</h3>
                    <p>Analyzes each review aspect separately using NLP</p>
                </div>
                
                <div class="feature">
                    <h3>📊 Multi-Aspect Reviews</h3>
                    <p>8 different review categories for detailed feedback</p>
                </div>
                
                <div class="feature">
                    <h3>📈 Analytics Dashboard</h3>
                    <p>Comprehensive insights and statistics</p>
                </div>
            </div>
            
            <div class="review-categories">
                <h3>Review Categories Analyzed:</h3>
                <ul>
                    <li>🔊 Sound Quality</li>
                    <li>💺 Seat Comfort</li>
                    <li>📏 Seat Height/Position</li>
                    <li>👀 View Quality</li>
                    <li>🎫 Booking Service</li>
                    <li>👥 Staff Behavior</li>
                    <li>✨ Cleanliness</li>
                    <li>💰 Value for Money</li>
                </ul>
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
                "message": "Seat already booked - Race condition prevented! Only first person gets the seat."
            }
        
        cur.execute("""
            UPDATE seats 
            SET status = 'booked', 
                user_id = %s,
                user_name = %s,
                booked_at = %s
            WHERE id = %s;
        """, (booking.user_id, booking.user_name, datetime.now(), seat_id))
        
        conn.commit()
        
        cur.execute(
            "SELECT seat_number FROM seats WHERE id = %s;",
            (seat_id,)
        )
        seat_number = cur.fetchone()[0]
        
        return {
            "status": "success",
            "message": "Seat booked successfully! Please submit your review.",
            "seat_number": seat_number,
            "seat_id": seat_id,
            "user_id": booking.user_id,
            "user_name": booking.user_name,
            "next_step": f"POST /review/{seat_id} to submit your detailed review"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cur.close()
        conn.close()

@app.post("/review/{seat_id}")
def submit_review(seat_id: int, review: ReviewRequest):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT status, user_id FROM seats WHERE id = %s;", (seat_id,))
        seat_data = cur.fetchone()
        
        if not seat_data:
            raise HTTPException(status_code=404, detail="Seat not found")
        
        if seat_data[0] != 'booked':
            raise HTTPException(status_code=400, detail="Cannot review an unbooked seat")
        
        overall_score, overall_label = analyze_sentiment(review.overall_experience)
        sound_score, sound_label = analyze_sentiment(review.sound_quality_review)
        comfort_score, comfort_label = analyze_sentiment(review.seat_comfort_review)
        height_score, height_label = analyze_sentiment(review.seat_height_review)
        view_score, view_label = analyze_sentiment(review.view_quality_review)
        booking_score, booking_label = analyze_sentiment(review.booking_service_review)
        staff_score, staff_label = analyze_sentiment(review.staff_behavior_review)
        clean_score, clean_label = analyze_sentiment(review.cleanliness_review)
        value_score, value_label = analyze_sentiment(review.value_for_money_review)
        
        scores = [overall_score, sound_score, comfort_score, height_score, view_score, 
                  booking_score, staff_score, clean_score, value_score]
        valid_scores = [s for s in scores if s != 0.0 or review.overall_experience]
        
        avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
        overall_rating = get_overall_rating(avg_score)
        
        cur.execute("""
            INSERT INTO reviews (
                seat_id, user_id, user_name,
                overall_experience, overall_sentiment_score, overall_sentiment_label,
                sound_quality_review, sound_quality_score, sound_quality_label,
                seat_comfort_review, seat_comfort_score, seat_comfort_label,
                seat_height_review, seat_height_score, seat_height_label,
                view_quality_review, view_quality_score, view_quality_label,
                booking_service_review, booking_service_score, booking_service_label,
                staff_behavior_review, staff_behavior_score, staff_behavior_label,
                cleanliness_review, cleanliness_score, cleanliness_label,
                value_for_money_review, value_for_money_score, value_for_money_label,
                average_score, overall_rating
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s
            );
        """, (
            seat_id, review.user_id, review.user_name,
            review.overall_experience, overall_score, overall_label,
            review.sound_quality_review, sound_score, sound_label,
            review.seat_comfort_review, comfort_score, comfort_label,
            review.seat_height_review, height_score, height_label,
            review.view_quality_review, view_score, view_label,
            review.booking_service_review, booking_score, booking_label,
            review.staff_behavior_review, staff_score, staff_label,
            review.cleanliness_review, clean_score, clean_label,
            review.value_for_money_review, value_score, value_label,
            avg_score, overall_rating
        ))
        
        conn.commit()
        
        return {
            "status": "success",
            "message": "Review submitted successfully!",
            "review_analysis": {
                "overall_experience": {"score": round(overall_score, 3), "sentiment": overall_label},
                "sound_quality": {"score": round(sound_score, 3), "sentiment": sound_label},
                "seat_comfort": {"score": round(comfort_score, 3), "sentiment": comfort_label},
                "seat_height": {"score": round(height_score, 3), "sentiment": height_label},
                "view_quality": {"score": round(view_score, 3), "sentiment": view_label},
                "booking_service": {"score": round(booking_score, 3), "sentiment": booking_label},
                "staff_behavior": {"score": round(staff_score, 3), "sentiment": staff_label},
                "cleanliness": {"score": round(clean_score, 3), "sentiment": clean_label},
                "value_for_money": {"score": round(value_score, 3), "sentiment": value_label},
                "average_score": round(avg_score, 3),
                "overall_rating": overall_rating
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cur.close()
        conn.close()

@app.get("/reviews")
def get_all_reviews():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            r.*,
            s.seat_number
        FROM reviews r
        JOIN seats s ON r.seat_id = s.id
        ORDER BY r.created_at DESC;
    """)
    
    reviews = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return {
        "total_reviews": len(reviews),
        "reviews": reviews
    }

@app.get("/reviews/{seat_id}")
def get_seat_review(seat_id: int):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            r.*,
            s.seat_number
        FROM reviews r
        JOIN seats s ON r.seat_id = s.id
        WHERE r.seat_id = %s
        ORDER BY r.created_at DESC;
    """, (seat_id,))
    
    reviews = cur.fetchall()
    
    cur.close()
    conn.close()
    
    if not reviews:
        raise HTTPException(status_code=404, detail="No reviews found for this seat")
    
    return {
        "seat_id": seat_id,
        "reviews": reviews
    }

@app.get("/analytics")
def get_analytics():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            COUNT(*) as total_reviews,
            AVG(overall_sentiment_score) as avg_overall_score,
            AVG(sound_quality_score) as avg_sound_score,
            AVG(seat_comfort_score) as avg_comfort_score,
            AVG(seat_height_score) as avg_height_score,
            AVG(view_quality_score) as avg_view_score,
            AVG(booking_service_score) as avg_booking_score,
            AVG(staff_behavior_score) as avg_staff_score,
            AVG(cleanliness_score) as avg_clean_score,
            AVG(value_for_money_score) as avg_value_score,
            AVG(average_score) as overall_avg_score,
            COUNT(*) FILTER (WHERE overall_sentiment_label = 'positive') as positive_overall,
            COUNT(*) FILTER (WHERE overall_sentiment_label = 'negative') as negative_overall,
            COUNT(*) FILTER (WHERE overall_sentiment_label = 'neutral') as neutral_overall,
            COUNT(*) FILTER (WHERE overall_rating = 'excellent') as excellent_ratings,
            COUNT(*) FILTER (WHERE overall_rating = 'good') as good_ratings,
            COUNT(*) FILTER (WHERE overall_rating = 'average') as average_ratings,
            COUNT(*) FILTER (WHERE overall_rating = 'poor') as poor_ratings,
            COUNT(*) FILTER (WHERE overall_rating = 'very_poor') as very_poor_ratings
        FROM reviews;
    """)
    
    stats = cur.fetchone()
    
    cur.execute("""
        SELECT 
            overall_sentiment_label as category,
            COUNT(*) as count
        FROM reviews
        GROUP BY overall_sentiment_label;
    """)
    
    sentiment_breakdown = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return {
        "overall_statistics": stats,
        "sentiment_breakdown": sentiment_breakdown,
        "category_scores": {
            "sound_quality": round(stats['avg_sound_score'] or 0, 3),
            "seat_comfort": round(stats['avg_comfort_score'] or 0, 3),
            "seat_height": round(stats['avg_height_score'] or 0, 3),
            "view_quality": round(stats['avg_view_score'] or 0, 3),
            "booking_service": round(stats['avg_booking_score'] or 0, 3),
            "staff_behavior": round(stats['avg_staff_score'] or 0, 3),
            "cleanliness": round(stats['avg_clean_score'] or 0, 3),
            "value_for_money": round(stats['avg_value_score'] or 0, 3)
        }
    }
