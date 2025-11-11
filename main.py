from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db_configs.firebase_db import db  # This triggers Firebase initialization
from routes import billing_routes, payment_routes, webhook_routes, invoice_routes, call_logs_route
from contextlib import asynccontextmanager


# Lifespan context manager for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize background scheduler
    print("\n🚀 Starting application...")
    from services.scheduler_service import start_scheduler
    
    # 🔥 run_on_startup=True: Updates DB immediately when server starts (for testing)
    # 💡 Later, change to run_on_startup=False to only run at midnight
    start_scheduler(run_on_startup=False)
    
    yield  # Application runs here
    
    # Shutdown: Stop background scheduler
    print("\n🛑 Shutting down application...")
    from services.scheduler_service import stop_scheduler
    stop_scheduler()


app = FastAPI(
    title="Billing & Payments Service",
    lifespan=lifespan
)

# Enable CORS (so your frontend can call the backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://billai.vysedeck.com",
        "http://portal.vysedeck.com:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(billing_routes.router, tags=["Billing"])
app.include_router(invoice_routes.router, tags=["Invoices"])
app.include_router(payment_routes.router, prefix="/payments", tags=["Payments"])
app.include_router(webhook_routes.router, prefix="/webhooks", tags=["Webhooks"])
#only for testing
app.include_router(call_logs_route.router)

@app.get("/")
def root():
    return {"message": "Billing & Payment API is running 🚀"}


# @app.get("/scheduler/status")
# def scheduler_status():
#     """
#     Check the status of the background scheduler and scheduled jobs.
#     """
#     from services.scheduler_service import get_scheduler_status
#     return get_scheduler_status()


# @app.post("/scheduler/run-now")
# def run_scheduler_now():
#     """
#     Manually trigger the overdue invoice update immediately (for testing/emergency).
#     """
#     from services.scheduler_service import run_overdue_update_now
#     run_overdue_update_now()
#     return {"message": "Overdue invoice update triggered manually"}
