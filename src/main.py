from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.market_engine import market_engine


app = FastAPI(title="Cahyonews AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "Cahyonews AI",
        "status": "online",
        "message": "Cahyonews AI API is running",
    }


@app.get("/api/market/status")
async def market_status():
    return market_engine.status()


@app.get("/api/market/xauusd")
async def xauusd_snapshot():
    return await market_engine.snapshot()


@app.get("/api/market/xauusd/candles")
async def xauusd_candles(
    timeframe: str = "M5",
    limit: int = 100,
):
    limit = max(1, min(limit, 500))
    return await market_engine.candles(timeframe, limit)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "cahyonews-ai",
    }


try:
    from workers import asgi

    asgi.entrypoint(app)
except ImportError:
    pass
