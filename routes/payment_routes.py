from fastapi import APIRouter, HTTPException, Depends, Query, Body
from auth.firebase_auth import verify_firebase_token
from repositories.invoice_repo import get_invoice_by_id
from services.payment_service import create_stripe_checkout_session, create_razorpay_order, verify_razorpay_payment
from utils.invoice_token import verify_invoice_token, generate_invoice_token
from pydantic import BaseModel

router = APIRouter()

# Pydantic model for payment verification request
class PaymentVerificationRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str

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
    payment_company_id = payload.get("payment_company_id")
    
    if tenant_id == "default":
        tenant_id = None
    
    print(f"Fetching invoice: company_id={company_id}, tenant_id={tenant_id}, invoice_id={invoice_id}")
    
    invoice = get_invoice_by_id(company_id, tenant_id, invoice_id)
    
    if not invoice:
        print(f"❌ Invoice NOT FOUND in Firestore")
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    print(f"✅ Invoice found")
    
    # Add the invoice_id to the invoice data
    invoice["invoice_number"] = invoice_id
    invoice["companyId"] = payment_company_id or company_id
    
    print("=" * 50)
    
    return create_razorpay_order(invoice)

@router.post("/generate-token")
def generate_payment_token(
    company_id: str = Query(...),
    tenant_id: str = Query(None),
    invoice_id: str = Query(...),
    payment_company_id: str = Query(None),
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
        token = generate_invoice_token(
            company_id, 
            tenant_id, 
            invoice_id, 
            payment_company_id=payment_company_id
        )
        
        print(f"✅ Token generated successfully")
        return {"token": token}
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ================== NEW ENDPOINT: VERIFY PAYMENT ==================
@router.post("/verify-payment")
def verify_payment_endpoint(
    payment_data: PaymentVerificationRequest = Body(...),
    token: str = Query(...)
):
    """
    Verifies Razorpay payment signature and processes the payment.
    This is the main endpoint called by the frontend after successful payment.
    """
    print("=" * 50)
    print("🔵 PAYMENT VERIFICATION REQUEST")
    print(f"Payment ID: {payment_data.razorpay_payment_id}")
    print(f"Order ID: {payment_data.razorpay_order_id}")
    print(f"Signature: {payment_data.razorpay_signature[:20]}...")
    
    try:
        # 1️⃣ Verify JWT token
        payload = verify_invoice_token(token)
        print(f"✅ Token verified: {payload}")
    except Exception as e:
        print(f"❌ Token verification failed: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    company_id = payload["company_id"]
    tenant_id = payload.get("tenant_id")
    invoice_id = payload["invoice_id"]
    payment_company_id = payload.get("payment_company_id")
    
    # Handle "default" tenant
    if tenant_id == "default":
        tenant_id = None
    
    print(f"📋 Invoice details: company={company_id}, tenant={tenant_id}, invoice={invoice_id}")
    
    try:
        # 2️⃣ Fetch invoice from Firestore
        invoice = get_invoice_by_id(company_id, tenant_id, invoice_id)
        
        if not invoice:
            print(f"❌ Invoice {invoice_id} not found")
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        print(f"✅ Invoice found")
        
        # 3️⃣ Check if already paid
        if invoice.get("payment_status") in ["paid", "due_paid"]:
            print(f"⚠️ Invoice {invoice_id} already marked as paid")
            return {
                "status": "already_paid",
                "message": "This invoice has already been paid",
                "invoice_id": invoice_id
            }
        
        # 4️⃣ Verify Razorpay signature and process payment
        result = verify_razorpay_payment(
            razorpay_payment_id=payment_data.razorpay_payment_id,
            razorpay_order_id=payment_data.razorpay_order_id,
            razorpay_signature=payment_data.razorpay_signature,
            invoice_data=invoice,
            company_id=company_id,
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            payment_company_id=payment_company_id
        )
        
        print(f"✅ Payment verification completed successfully")
        print("=" * 50)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Payment verification failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")