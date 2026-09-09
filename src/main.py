from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
        "message": "Cahyonews AI API is running"
    }

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "cahyonews-ai"
    }
