from fastapi import APIRouter, HTTPException, Depends, Query
from auth.firebase_auth import verify_firebase_token
from repositories.invoice_repo import get_invoice_by_id
from services.payment_service import create_stripe_checkout_session, create_razorpay_order
from utils.invoice_token import verify_invoice_token

router = APIRouter()

@router.post("/create-session/stripe")
def create_stripe_session( token: str = Query(...) ):
    try:
        payload = verify_invoice_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    company_id = payload["company_id"]
    tenant_id = payload["tenant_id"]
    invoice_id = payload["invoice_id"]
    invoice = get_invoice_by_id(company_id, tenant_id, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return create_stripe_checkout_session(invoice)

@router.post("/create-order/razorpay")
def create_razorpay_order_route( token: str = Query(...) ):
    try:
        payload = verify_invoice_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    company_id = payload["company_id"]
    tenant_id = payload["tenant_id"]
    invoice_id = payload["invoice_id"]
    invoice = get_invoice_by_id(company_id, tenant_id, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return create_razorpay_order(invoice)
