import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import check_db_connection
from backend.api import auth as auth_router
from backend.api import users as users_router
from backend.api import transactions as transactions_router
from backend.api import upload as upload_router
from backend.api.categorise import router as categorise_router
from backend.api.summary import router as summary_router
from backend.api.qa import router as qa_router
from backend.api.anomalies import router as anomalies_router
from backend.api.forecast import router as forecast_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s"
)

# Create the FastAPI app
app = FastAPI(
    title="FinCopilot API",
    description="AI-powered bookkeeping assistant for UK SMEs",
    version="1.0.0"
)

# CORS — allows React frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # React dev server
        "http://localhost:3000",  # alternate React port
    ],
    allow_credentials=True,
    allow_methods=["*"],  # allow GET, POST, PATCH, DELETE etc
    allow_headers=["*"],  # allow Authorization header for JWT
)

@app.get("/")
def root():
    """
    Basic health check — confirms API is running.
    """
    return {"message": "FinCopilot API is running"}

@app.get("/health")
def health_check():
    """
    Confirms API is running AND database is connected.
    """
    db_connected = check_db_connection()

    return {
        "status": "ok",
        "database": "connected" if db_connected else "disconnected"
    }

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(transactions_router.router)
app.include_router(upload_router.router)
app.include_router(categorise_router)
app.include_router(summary_router)
app.include_router(qa_router)
app.include_router(anomalies_router)
app.include_router(forecast_router)