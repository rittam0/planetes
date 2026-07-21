from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import objects, asteroids, conjunctions, investigate, metrics

app = FastAPI(
    title="Planetes Backend",
    description="Autonomous Space Intelligence Platform - LangGraph + SGP4 + NASA NeoWs + KeepTrack + Groq",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(objects.router)
app.include_router(asteroids.router)
app.include_router(conjunctions.router)
app.include_router(investigate.router)
app.include_router(metrics.router)

@app.get("/")
async def root():
    return {
        "status": "Planetes API running",
        "version": "1.0.0",
        "features": [
            "Live KeepTrack satellite catalog (30+ satellites with real TLEs)",
            "Live NASA NeoWs asteroid tracking",
            "SGP4 orbital propagation on real TLE data",
            "LangGraph multi-agent AI investigation",
            "Groq LLM structured report generation",
            "Physics-informed conjunction risk scoring"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
