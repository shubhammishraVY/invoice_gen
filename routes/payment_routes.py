from fastapi import APIRouter, HTTPException, Depends, Query
from auth.firebase_auth import verify_firebase_token
from repositories.invoice_repo import get_invoice_by_id
from services.payment_service import create_stripe_checkout_session, create_razorpay_order
from utils.invoice_token import verify_invoice_token, generate_invoice_token

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
    print("=" * 50)
    print("🔵 CREATE RAZORPAY ORDER REQUEST")
    
    try:
        payload = verify_invoice_token(token)
        print(f"✅ Token verified: {payload}")
    except Exception as e:
        print(f"❌ Token verification failed: {e}")
        raise HTTPException(status_code=401, detail=str(e))

    company_id = payload["company_id"]
    tenant_id = payload.get("tenant_id")
    invoice_id = payload["invoice_id"]
    
    if tenant_id == "default":
        tenant_id = None
    
    print(f"Fetching invoice: company_id={company_id}, tenant_id={tenant_id}, invoice_id={invoice_id}")
    
    invoice = get_invoice_by_id(company_id, tenant_id, invoice_id)
    
    if not invoice:
        print(f"❌ Invoice NOT FOUND in Firestore")
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    print(f"✅ Invoice found")
    
    # Add the invoice_id to the invoice data
    invoice["invoice_number"] = invoice_id  # ← ADD THIS LINE
    
    print("=" * 50)
    
    return create_razorpay_order(invoice)

@router.post("/generate-token")
def generate_payment_token(
    company_id: str = Query(...),
    tenant_id: str = Query(None),
    invoice_id: str = Query(...),
    user: dict = Depends(verify_firebase_token)
):
    # Treat "default" tenant as None for downstream lookup
    if tenant_id == "default":
        tenant_id = None

    print("=" * 50)
    print("🔵 GENERATE TOKEN REQUEST RECEIVED")
    print(f"company_id: {company_id}")
    print(f"tenant_id: {tenant_id}")
    print(f"invoice_id: {invoice_id}")
    print(f"user: {user}")
    print("=" * 50)
    
    try:
        token = generate_invoice_token(company_id, tenant_id, invoice_id)
        
        print(f"✅ Token generated successfully")
        return {"token": token}
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
