import os
import psycopg2
from fastapi import FastAPI, HTTPException
from psycopg2.extras import RealDictCursor
from contextlib import asynccontextmanager

DATABASE_URL = os.environ.get("DATABASE_URL")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs every time the app starts up
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
        # We are creating 10 seats here
        seats = [(f'A{i}',) for i in range(1, 11)]
        cur.executemany("INSERT INTO seats (seat_number) VALUES (%s);", seats)
    conn.commit()
    cur.close()
    conn.close()
    yield

app = FastAPI(title="Booking Engine", lifespan=lifespan)

@app.get("/seats", tags=["Dashboard"], summary="Show all 10 seats")
def get_seats():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM seats ORDER BY id;")
    seats = cur.fetchall()
    cur.close()
    conn.close()
    return seats

@app.post("/book/{seat_id}", tags=["Booking"], summary="Book a seat")
def book_seat(seat_id: int, user_id: int):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    try:
        # LOCKING logic starts here
        cur.execute("SELECT status FROM seats WHERE id = %s FOR UPDATE;", (seat_id,))
        row = cur.fetchone()
        if not row:
            return {"message": f"❌ Error: Seat ID {seat_id} doesn't exist. Check /seats for valid IDs."}
        if row[0] == 'available':
            cur.execute("UPDATE seats SET status = 'booked', user_id = %s WHERE id = %s;", (user_id, seat_id))
            conn.commit()
            return {"message": f"✅ Success! Seat {seat_id} is yours."}
        return {"message": "❌ Too late! This seat is already taken."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()

@app.post("/reset", tags=["Admin"], summary="Wipe everything and start over")
def reset_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    # This clears the table and resets IDs to start at 1
    cur.execute("TRUNCATE TABLE seats RESTART IDENTITY;")
    seats = [(f'A{i}',) for i in range(1, 11)]
    cur.executemany("INSERT INTO seats (seat_number) VALUES (%s);", seats)
    conn.commit()
    cur.close()
    conn.close()
    return {"message": "Database wiped. You now have 10 fresh seats (IDs 1-10)."}
