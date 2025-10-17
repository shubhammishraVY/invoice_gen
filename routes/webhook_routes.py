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
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    secret = os.getenv("RAZORPAY_KEY_SECRET")

    generated_signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    if generated_signature != signature:
        raise HTTPException(status_code=400, detail="Signature mismatch")

    event = await request.json()
    if event.get("event") == "payment.captured":
        payment_data = event["payload"]["payment"]["entity"]
        
        # Extract invoice details from notes
        invoice_id = payment_data["notes"].get("invoice_id")
        company_id = payment_data["notes"].get("company_id")
        tenant_id = payment_data["notes"].get("tenant_id", "default")
        
        print(f"✅ Razorpay payment captured for invoice {invoice_id}")
        
        # Fetch full invoice data
        invoice = get_invoice_by_id(company_id, tenant_id, invoice_id)
        if not invoice:
            print(f"❌ Invoice {invoice_id} not found")
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Prepare payment data for receipt generation
        payment_info = {
            **invoice,
            "payment_id": payment_data["id"],
            "payment_date": datetime.utcnow().isoformat(),
            "payment_mode": "Razorpay",
        }
        
        # Generate receipt and mark as paid
        generate_payment_receipt(payment_info)

    return {"status": "success"}
