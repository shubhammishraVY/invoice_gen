from fastapi import FastAPI
from routes import billing_routes

app = FastAPI(
    title="Billing for Calls",
    version="1.0.0",
    description="FastAPI service for generating call bills"
)

# Include billing router
app.include_router(billing_routes.router, prefix="/billing", tags=["Billing"])

# Health check
@app.get("/")
def root():
    return {"message": "Billing API is running!"}
