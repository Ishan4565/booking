import os
import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from psycopg2.extras import RealDictCursor
from contextlib import asynccontextmanager
from pydantic import BaseModel

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

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
            user_name VARCHAR(100)
        );
    """)
    
    cur.execute("SELECT count(*) FROM seats;")
    if cur.fetchone()[0] == 0:
        seats = [
            ('A1',), ('A2',), ('A3',), ('A4',), ('A5',),
            ('B1',), ('B2',), ('B3',), ('B4',), ('B5',),
            ('C1',), ('C2',), ('C3',), ('C4',), ('C5',)
        ]
        cur.executemany("INSERT INTO seats (seat_number) VALUES (%s);", seats)
    
    conn.commit()
    cur.close()
    conn.close()
    
    yield

app = FastAPI(
    title="🎫 Seat Booking System",
    description="Simple and clean seat reservation API with race condition prevention",
    version="1.0.0",
    lifespan=lifespan
)

class BookingRequest(BaseModel):
    user_name: str
    user_id: int

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Seat Booking System</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 900px;
                margin: 50px auto;
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
                margin-bottom: 40px;
            }
            .endpoint {
                background: #f8f9fa;
                border-left: 4px solid #667eea;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
            }
            .method {
                display: inline-block;
                padding: 5px 15px;
                border-radius: 5px;
                font-weight: bold;
                color: white;
                margin-right: 10px;
            }
            .get { background: #28a745; }
            .post { background: #007bff; }
            .path {
                font-family: 'Courier New', monospace;
                color: #333;
                font-size: 18px;
            }
            .description {
                margin-top: 10px;
                color: #555;
            }
            .example {
                background: #f0f0f0;
                padding: 15px;
                border-radius: 5px;
                margin-top: 10px;
                font-family: 'Courier New', monospace;
                font-size: 14px;
            }
            .btn {
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 12px 30px;
                text-decoration: none;
                border-radius: 8px;
                margin-top: 30px;
                text-align: center;
                display: block;
                font-weight: bold;
            }
            .btn:hover {
                background: #764ba2;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎫 Seat Booking System</h1>
            <p class="subtitle">Race Condition Prevention | First-Come First-Served</p>
            
            <div class="endpoint">
                <div>
                    <span class="method get">GET</span>
                    <span class="path">/seats</span>
                </div>
                <p class="description">View all available seats and booking status</p>
                <div class="example">
                    Response: List of all seats with availability status
                </div>
            </div>
            
            <div class="endpoint">
                <div>
                    <span class="method post">POST</span>
                    <span class="path">/book/{seat_id}</span>
                </div>
                <p class="description">Book a specific seat by ID</p>
                <div class="example">
                    Request Body:<br>
                    {<br>
                    &nbsp;&nbsp;"user_name": "John Doe",<br>
                    &nbsp;&nbsp;"user_id": 123<br>
                    }
                </div>
            </div>
            
            <a href="/docs" class="btn">📖 Open Interactive API Documentation</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/seats")
def get_all_seats():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT * FROM seats ORDER BY seat_number;")
    seats = cur.fetchall()
    
    available_count = sum(1 for seat in seats if seat['status'] == 'available')
    total_count = len(seats)
    
    cur.close()
    conn.close()
    
    return {
        "total_seats": total_count,
        "available_seats": available_count,
        "booked_seats": total_count - available_count,
        "seats": seats
    }

@app.post("/book/{seat_id}")
def book_seat(seat_id: int, booking: BookingRequest):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT status FROM seats WHERE id = %s FOR UPDATE;", (seat_id,))
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Seat not found")
        
        if row[0] == 'available':
            cur.execute(
                "UPDATE seats SET status = 'booked', user_id = %s, user_name = %s WHERE id = %s;",
                (booking.user_id, booking.user_name, seat_id)
            )
            conn.commit()
            
            cur.execute(
                "SELECT seat_number, status, user_name FROM seats WHERE id = %s;",
                (seat_id,)
            )
            booked_seat = cur.fetchone()
            
            return {
                "message": "Seat booked successfully!",
                "seat_number": booked_seat[0],
                "user_name": booked_seat[2],
                "status": "confirmed"
            }
        else:
            return {
                "message": "Seat already taken",
                "status": "failed"
            }
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cur.close()
        conn.close()
