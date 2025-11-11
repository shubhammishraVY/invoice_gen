# webhook_routes.py
from fastapi import APIRouter, Request, HTTPException
import os, hmac, hashlib, stripe
from dotenv import load_dotenv
from datetime import datetime
from services.payment_service import generate_payment_receipt
from repositories.invoice_repo import get_invoice_by_id
from services.razorpay_config import get_razorpay_credentials  # ✅ NEW IMPORT

load_dotenv()
router = APIRouter()

# -------------------- STRIPE --------------------
@router.post("/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Stripe payload: {e}")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        invoice_id = session["metadata"].get("invoice_id")
        print(f"✅ Stripe payment successful for invoice {invoice_id}")
        generate_payment_receipt(invoice_id, payment_data=session)

    return {"status": "success"}


# -------------------- RAZORPAY --------------------
@router.post("/razorpay")
async def razorpay_webhook(request: Request):
    """
    Razorpay webhook endpoint - serves as a BACKUP mechanism.
    Now uses company-specific credentials for signature verification.
    """
    print("=" * 50)
    print("📩 RAZORPAY WEBHOOK RECEIVED")
    
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    
    # ⚠️ We need to get company_id from payload first to fetch the right secret
    event = await request.json()
    
    # Extract company_id from notes
    payment_data = event.get("payload", {}).get("payment", {}).get("entity", {})
    company_id = payment_data.get("notes", {}).get("company_id")
    
    if not company_id:
        print("❌ Company ID not found in webhook payload")
        raise HTTPException(status_code=400, detail="Company ID not found in webhook")
    
    print(f"🏢 Company ID from webhook: {company_id}")
    
    # Fetch company-specific secret
    try:
        _, secret = get_razorpay_credentials(company_id)
    except Exception as e:
        print(f"❌ Failed to fetch Razorpay credentials: {e}")
        raise HTTPException(status_code=400, detail="Failed to fetch Razorpay credentials")

    # Verify signature
    generated_signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    if generated_signature != signature:
        print("❌ Webhook signature mismatch")
        raise HTTPException(status_code=400, detail="Signature mismatch")

    print("✅ Webhook signature verified")
    
    if event.get("event") == "payment.captured":
        print("✅ Payment captured event detected!")
        
        # Extract invoice details from notes
        invoice_id = payment_data["notes"].get("invoice_id")
        tenant_id = payment_data["notes"].get("tenant_id")
        
        if tenant_id == "default":
            tenant_id = None
        
        print(f"📋 Invoice ID from webhook: {invoice_id}")
        print(f"   Company: {company_id}")
        print(f"   Tenant: {tenant_id}")
        
        # Fetch full invoice data
        invoice = get_invoice_by_id(company_id, tenant_id, invoice_id)
        
        if not invoice:
            print(f"❌ Invoice {invoice_id} not found")
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        print(f"✅ Invoice found")
        
        # Check if already paid
        if invoice.get("payment_status") in ["paid", "due_paid"]:
            print(f"⚠️ Invoice {invoice_id} already marked as paid - skipping webhook processing")
            return {"status": "already_processed", "message": "Invoice already paid"}
        
        # Prepare payment data
        payment_info = {
            **invoice,
            "invoice_number": invoice_id,
            "companyId": company_id,
            "tenant_id": tenant_id,
            "payment_id": payment_data["id"],
            "order_id": payment_data.get("order_id"),
            "payment_date": datetime.utcnow().isoformat(),
            "payment_mode": "Razorpay",
        }
        
        print(f"📧 Processing payment via webhook...")
        
        # Generate receipt and update database
        result = generate_payment_receipt(payment_info)
        
        if result.get("status") == "success":
            print(f"✅ Webhook payment processing completed successfully")
        else:
            print(f"⚠️ Webhook processing encountered issues: {result.get('message')}")
        
        print("=" * 50)
        return {"status": "success", "result": result}
    
    else:
        print(f"ℹ️ Unhandled webhook event: {event.get('event')}")
        return {"status": "ignored", "event": event.get("event")}

    return {"status": "success"}