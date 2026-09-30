import os
from contextlib import asynccontextmanager

import redis.asyncio as redis
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import auth, chat, reports

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):  # Get client on startup, close on shutdown
    app.state.redis_client = redis.from_url(
        os.getenv("REDIS_BROKER_URL", "redis://localhost:6379/0")
    )
    yield
    await app.state.redis_client.aclose()


app = FastAPI(title="Multi-Agent Research API", lifespan=lifespan)

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/get-data")
def get_data():
    #talk to database
    return{"msg":"hi"}

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, tags=["chat"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
