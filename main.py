import os
import psycopg2
from fastapi import FastAPI, HTTPException

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL")

# --- NEW: This function creates your tables automatically ---
from contextlib import asynccontextmanager

# This is the modern "Lifespan" way
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP LOGIC ---
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    try:
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
        print("✅ Database ready (Lifespan Startup)")
    finally:
        cur.close()
        conn.close()
    
    yield  # This separates Startup from Shutdown
    
    # --- SHUTDOWN LOGIC ---
    print("🧹 Cleaning up (Lifespan Shutdown)")

# Tell FastAPI to use this lifespan manager
app = FastAPI(lifespan=lifespan)