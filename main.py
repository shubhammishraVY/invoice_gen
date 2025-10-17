from fastapi import FastAPI
from routes import billing_routes, payment_routes, webhook_routes, invoice_routes, call_logs_route
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Billing & Payments Service")

# Enable CORS (so your frontend can call the backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://portal.vysedeck.com:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
 
app.include_router(invoice_routes.router, tags=["Invoices"])
app.include_router(payment_routes.router, prefix="/payments", tags=["Payments"])
app.include_router(webhook_routes.router, prefix="/webhooks", tags=["Webhooks"])
#only for testing
app.include_router(call_logs_route.router)

@app.get("/")
def root():
    return {"message": "Billing & Payment API is running 🚀"}
