from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.websockets import WebSocket
from loguru import logger

from .api.routes import analysis, credit, reports
from .api.websocket import websocket_endpoint

app = FastAPI(
    title="Multi-Agent Investment Intelligence Platform",
    description="5-agent LLM system for investment analysis and credit risk scoring",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router)
app.include_router(credit.router)
app.include_router(reports.router)


@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    await websocket_endpoint(websocket)


@app.get("/")
async def root():
    return {
        "name": "Multi-Agent Investment Intelligence Platform",
        "version": "1.0.0",
        "endpoints": {
            "analyze": "POST /api/analyze/{ticker}",
            "status": "GET /api/analyze/status/{ticker}",
            "credit": "GET /api/credit/{ticker}",
            "report": "GET /api/reports/{ticker}/pdf",
            "websocket": "WS /ws",
            "docs": "/docs",
        },
    }


@app.on_event("startup")
async def startup():
    logger.info("Investment Intelligence Platform starting up...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
