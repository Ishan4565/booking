import os
import psycopg2
from fastapi import FastAPI, HTTPException
from psycopg2.extras import RealDictCursor
from contextlib import asynccontextmanager

# 1. Database Connection Configuration
DATABASE_URL = os.environ.get("DATABASE_URL")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles database setup when the app starts."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    # Create the table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS seats (
            id SERIAL PRIMARY KEY,
            seat_number VARCHAR(10) UNIQUE NOT NULL,
            status VARCHAR(20) DEFAULT 'available',
            user_id INTEGER
        );
    """)
    # Fill with 10 seats if empty
    cur.execute("SELECT count(*) FROM seats;")
    if cur.fetchone()[0] == 0:
        seats = [(f'A{i}',) for i in range(1, 11)]
        cur.executemany("INSERT INTO seats (seat_number) VALUES (%s);", seats)
    conn.commit()
    cur.close()
    conn.close()
    yield

# 2. Initialize FastAPI with a clean Title and Description
app = FastAPI(
    title="🏢 Pro Booking Engine",
    description="Backend API with Pessimistic Locking logic. Use the 'Reset' endpoint to clear data.",
    lifespan=lifespan,
    version="1.0.0"
)

# 3. Routes (Cleaned up with Tags and Summaries)

@app.get("/seats", tags=["User Dashboard"], summary="View All Available Seats")
def get_seats():
    """Fetches the current status of every seat in the database."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM seats ORDER BY id;")
    seats = cur.fetchall()
    cur.close()
    conn.close()
    return seats

@app.post("/book/{seat_id}", tags=["Booking Actions"], summary="Confirm a Reservation")
def book_seat(seat_id: int, user_id: int):
    """Books a seat using Pessimistic Locking to prevent double-booking."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    try:
        # The 'FOR UPDATE' lock prevents race conditions
        cur.execute("SELECT status FROM seats WHERE id = %s FOR UPDATE;", (seat_id,))
        row = cur.fetchone()
