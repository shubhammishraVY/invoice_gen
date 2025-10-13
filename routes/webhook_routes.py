from fastapi import APIRouter, Request, HTTPException
import os, hmac, hashlib, stripe
from dotenv import load_dotenv
from services.payment_service import generate_payment_receipt

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
        invoice_id = payment_data["notes"].get("invoice_id", "unknown")
        print(f"✅ Razorpay payment captured for invoice {invoice_id}")

        # 🔹 Call your unified service
        generate_payment_receipt(invoice_id, payment_data=payment_data)

    return {"status": "success"}
