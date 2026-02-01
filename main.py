import os
import psycopg2
from fastapi import FastAPI, HTTPException
from psycopg2.extras import RealDictCursor
from contextlib import asynccontextmanager

DATABASE_URL = os.getenv("postgresql://booking_db_ymh9_user:K33DWn4uZQTHUmQQHkDVd9uNNHmzL557@dpg-d5vh8nqqcgvc739kdte0-a/booking_db_ymh9")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Setup database
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS seats (
            id SERIAL PRIMARY KEY,
            seat_number VARCHAR(10) UNIQUE NOT NULL,
            status VARCHAR(20) DEFAULT 'available',
            user_id INTEGER
        );
    """)
    cur.execute("SELECT count(*) FROM seats;")
    if cur.fetchone()[0] == 0:
        seats = [('A1',), ('A2',), ('A3',), ('B1',), ('B2',)]
        cur.executemany("INSERT INTO seats (seat_number) VALUES (%s);", seats)
    conn.commit()
    cur.close()
    conn.close()
    yield

# 1. CREATE THE APP (Must be before the routes!)
app = FastAPI(lifespan=lifespan)

# 2. DEFINE THE ROUTES (The "Green and Blue" buttons)
@app.get("/seats")
def get_seats():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM seats ORDER BY id;")
    seats = cur.fetchall()
    cur.close()
    conn.close()
    return seats

@app.post("/book/{seat_id}")
def book_seat(seat_id: int, user_id: int):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    try:
        # PESSIMISTIC LOCKING logic
        cur.execute("SELECT status FROM seats WHERE id = %s FOR UPDATE;", (seat_id,))
        row = cur.fetchone()
        if row and row[0] == 'available':
            cur.execute("UPDATE seats SET status = 'booked', user_id = %s WHERE id = %s;", (user_id, seat_id))
            conn.commit()
            return {"message": "Success!"}
        return {"message": "Seat taken"}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()
