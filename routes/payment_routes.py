from fastapi import APIRouter, HTTPException, Depends
from auth.firebase_auth import verify_firebase_token
from repositories.invoice_repo import get_invoice_by_id
from services.payment_service import create_stripe_checkout_session, create_razorpay_order

router = APIRouter()

@router.post("/create-session/stripe")
def create_stripe_session(company_id: str, invoice_id: str, user=Depends(verify_firebase_token)):
    invoice = get_invoice_by_id(company_id, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return create_stripe_checkout_session(invoice)

@router.post("/create-order/razorpay")
def create_razorpay_order_route(company_id: str, invoice_id: str, user=Depends(verify_firebase_token)):
    invoice = get_invoice_by_id(company_id, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return create_razorpay_order(invoice)
