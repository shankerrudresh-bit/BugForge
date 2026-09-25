from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import architectures, scenarios, runs

app = FastAPI(
    title="BugForge API",
    description="AI-driven chaos engineering platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(architectures.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")
app.include_router(runs.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "service": "bugforge-backend"}
