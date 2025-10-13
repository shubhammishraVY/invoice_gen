from fastapi import APIRouter, Depends, HTTPException
from auth.firebase_auth import verify_firebase_token
from repositories.invoice_repo import get_invoice_by_id

router = APIRouter()

@router.get("/invoices/{company_id}/{invoice_id}")
def get_invoice_data(company_id: str, invoice_id: str, user=Depends(verify_firebase_token)):
    invoice_data = get_invoice_by_id(company_id, invoice_id)
    if not invoice_data:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Optional: Restrict invoice access by email
    # if user["email"] != invoice.get("companyInfo", {}).get("billingEmail"):
    #     raise HTTPException(status_code=403, detail="Not authorized to view this invoice")

    return invoice_data