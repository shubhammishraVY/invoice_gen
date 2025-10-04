from fastapi import APIRouter, Query
from services.billing_service import generate_monthly_bill, generate_monthly_bill_for_all
from reqResVal_models.billing_models import InvoiceModel

router = APIRouter()

# @router.get("/generate", response_model=InvoiceModel)
# def generate_bill(
#     company: str = "vysedeck",
#     month: int | None = Query(None, description="Month (1-12). Defaults to last completed month"),
#     year: int | None = Query(None, description="Year. Defaults to current year if not provided")
# ):
#     try:
#         result = generate_monthly_bill(company, month, year)
#         return result
#     except ValueError as e:
#         return {"error": str(e)}


#for testing purpose
@router.post("/generate-all")
def generate_all_invoices():
    invoices = generate_monthly_bill_for_all()
    return {"status": "completed", "generated": len(invoices), "invoices": invoices}

