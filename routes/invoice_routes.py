from fastapi import APIRouter, HTTPException, Query
from utils.invoice_token import verify_invoice_token
from repositories.invoice_repo import get_invoice_by_id

router = APIRouter()

@router.get("/invoices/token")
def get_invoice_by_token(token: str = Query(...)):
    try:
        payload = verify_invoice_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    company_id = payload["company_id"]
    tenant_id = payload["tenant_id"]
    invoice_id = payload["invoice_id"]

    
    invoice_data = get_invoice_by_id(company_id, tenant_id, invoice_id)
    
    if not invoice_data:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice_data.get("paid"):
        return {"paid": True, "payment_info": invoice_data.get("payment_info")}
    else:
        return {"paid": False, "invoice": invoice_data}
