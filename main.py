import os
import psycopg2
from fastapi import FastAPI, HTTPException
from psycopg2.extras import RealDictCursor
from contextlib import asynccontextmanager

# Database Connection
DATABASE_URL = os.environ.get("DATABASE_URL")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create table and seed data
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
        seats = [(f'Seat-{i}',) for i in range(1, 11)]
        cur.executemany("INSERT INTO seats (seat_number) VALUES (%s);", seats)
    conn.commit()
    cur.close()
    conn.close()
    yield

app = FastAPI(
    title="Seat Booking API",
    lifespan=lifespan
)

@app.get("/seats", tags=["Dashboard"])
def get_seats():
    """Check availability of all seats."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM seats ORDER BY id;")
    seats = cur.fetchall()
    cur.close()
    conn.close()
    return seats

@app.post("/book/{seat_id}", tags=["Booking"])
def book_seat(seat_id: int, user_id: int):
    """Books a seat using Pessimistic Locking."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    try:
        # Lock the row to prevent race conditions
        cur.execute("SELECT status FROM seats WHERE id = %s FOR UPDATE;", (seat_id,))
        row = cur.fetchone()
        if not row:
            return {"message": "Error: Seat not found"}
        if row[0] == 'available':
            cur.execute("UPDATE seats SET status = 'booked', user_id = %s WHERE id = %s;", (user_id, seat_id))
            conn.commit()
            return {"message": "✅ Success! Seat booked."}
        else:
            return {"message": "❌ Already taken."}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()

@app.post("/reset", tags=["Admin"])
def reset_db():
    """Wipes the table and resets IDs to start at 1."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    # This command clears the table and restarts the ID counter at 1
    cur.execute("TRUNCATE TABLE seats RESTART IDENTITY;")
    # Re-fill the 10 seats
    seats = [(f'Seat-{i}',) for i in range(1, 11)]
    cur.executemany("INSERT INTO seats (seat_number) VALUES (%s);", seats)
    conn.commit()
    cur.close()
    conn.close()
    return {"message": "Database wiped and IDs reset to 1!"}
