from fastapi import APIRouter, Request, HTTPException
import os, hmac, hashlib, stripe
from dotenv import load_dotenv
from datetime import datetime
from services.payment_service import generate_payment_receipt
from repositories.invoice_repo import get_invoice_by_id

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

        # 🔹 Call your unified service
        generate_payment_receipt(invoice_id, payment_data=session)

    return {"status": "success"}


# -------------------- RAZORPAY --------------------
@router.post("/razorpay")
async def razorpay_webhook(request: Request):
    """
    Razorpay webhook endpoint - serves as a BACKUP mechanism.
    The primary payment verification happens via the /verify-payment endpoint.
    This webhook ensures payments are recorded even if the frontend fails to call verify-payment.
    """
    print("=" * 50)
    print("🔔 RAZORPAY WEBHOOK RECEIVED")
    
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    secret = os.getenv("RAZORPAY_KEY_SECRET")

    # Optional: Verify webhook signature (recommended for production)
    # generated_signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    # if generated_signature != signature:
    #     print("❌ Webhook signature mismatch")
    #     raise HTTPException(status_code=400, detail="Signature mismatch")

    event = await request.json()
    
    if event.get("event") == "payment.captured":
        print("✅ Payment captured event detected!")
        
        payment_data = event["payload"]["payment"]["entity"]
        
        # Extract invoice details from notes
        invoice_id = payment_data["notes"].get("invoice_id")
        company_id = payment_data["notes"].get("company_id")
        tenant_id = payment_data["notes"].get("tenant_id")
        
        # Handle "default" tenant
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
        
        # Check if already paid (to avoid duplicate processing)
        if invoice.get("payment_status") in ["paid", "due_paid"]:
            print(f"⚠️ Invoice {invoice_id} already marked as paid - skipping webhook processing")
            return {"status": "already_processed", "message": "Invoice already paid"}
        
        # Prepare payment data for receipt generation
        payment_info = {
            **invoice,  # Spread invoice data
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