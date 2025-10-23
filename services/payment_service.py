import stripe
import razorpay
import os
from dotenv import load_dotenv
from datetime import datetime
from services.pdf_service import generate_pdf
from services.mailer_service import send_email
from repositories.bill_repo import save_payment_record, mark_invoice_as_paid
load_dotenv()

#--- Stripe Setup ---
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

#--- Razorpay Setup ---
razorpay_client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)

def create_stripe_checkout_session(invoice_data):
    """
    Creates a Stripe checkout session for an invoice.

    """
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data":{
                        "currency": "inr",
                        "product_data": {"name": f"Invoice {invoice_data['invoice_number']}"},
                        "unit_amount": int(invoice_data["totalAmount"] * 100),
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=f"{os.getenv('FRONTEND_URL')}/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{os.getenv('FRONTEND_URL')}/payment-failed",
            metadata={"invoice_id": invoice_data["invoice_number"]},
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise Exception(f"Stripe session creation failed: {e}")
    
def create_razorpay_order(invoice_data):
    try:
        order = razorpay_client.order.create({
            "amount": int(invoice_data["totalAmount"] * 100),
            "currency": "INR",
            "receipt": invoice_data["invoice_number"],
            "notes": {
                "invoice_id": invoice_data["invoice_number"],
                "company_id": invoice_data.get("companyId"),
                "tenant_id": invoice_data.get("tenant_id", "default"),
            }
        })
        return order
    except Exception as e:
        raise Exception(f"Razorpay order creation failed: {e}")
    










def generate_payment_receipt(payment_data: dict):
    """
    Generates a payment receipt PDF and emails it to the client.
    Reuses the generic PDF and mailer services.
    """
    try:
        company_info = payment_data.get("companyInfo", {})
        recipient_email = company_info.get("billingEmail")
        company_name = company_info.get("legalName", "Valued Client")
        invoice_number = payment_data.get("invoice_number")
        payment_id = payment_data.get("payment_id")
        payment_date = payment_data.get("payment_date", datetime.utcnow().isoformat())
        total_amount = payment_data.get("totalAmount", 0)
        payment_mode = payment_data.get("payment_mode", "Online")
        currency = payment_data.get("currency", "INR")
        companyId = payment_data.get("companyId")

        # --- 1️⃣ Generate PDF ---
        receipt_data = {
            "receipt_number": f"RCPT-{payment_id}",
            "invoice_number": invoice_number,
            "company_name": company_name,
            "amount_paid": total_amount,
            "currency_symbol": "₹" if currency == "INR" else currency,
            "payment_mode": payment_mode,
            "payment_date": payment_date[:10],
            "authorized_signatory": {
                "name": "Shashank Trivedi",
                "designation": "Director",
                "company": "VYSEDECK AI Ventures Pvt Ltd"
            }
        }

        pdf_path = generate_pdf("receipt_template.html", receipt_data, prefix="receipt")

        # --- 2️⃣ Send Email ---
        subject = f"Payment Receipt for Invoice {invoice_number}"
        context = {
            "company_name": company_name,
            "invoice_number": invoice_number,
            "receipt_number": receipt_data["receipt_number"],
            "amount_paid": f"{total_amount:,.2f}",
            "payment_mode": payment_mode,
            "payment_date": receipt_data["payment_date"],
            "currency_symbol": receipt_data["currency_symbol"],
            "sender_email": os.getenv("SENDER_EMAIL"),
            "payment_url": f"{os.getenv('FRONTEND_URL', 'http://portal.vysedeck.com:5173')}/payments",
        }

        send_email(
            # recipient_email=recipient_email,
            recipient_email="vishruth.ramesh@vysedeck.com",#for testing purposes
            subject=subject,
            html_template="receipt_email_template.html",
            context=context,
            attachments=[pdf_path],
        )

        print(f"✅ Payment receipt emailed successfully to {recipient_email}")

        # --- 3️⃣ Save COMPLETE Payment Record in payments collection ---
        save_payment_record(companyId, {
            "payment_id": payment_id,
            "invoice_number": invoice_number,
            "amount_paid": total_amount,
            "currency": currency,
            "payment_date": payment_date,
            "payment_mode": payment_mode,
            "receipt_pdf": pdf_path,
            "razorpay_order_id": payment_data.get("order_id"),  # Optional
            "razorpay_signature": payment_data.get("razorpay_signature"),  # Optional
        })

        # --- 4️⃣ Update ONLY payment_status in invoice ---
        mark_invoice_as_paid(companyId, invoice_number, {})  # Pass empty dict since we only update status

        return {"status": "success", "receipt_pdf": pdf_path}

    except Exception as e:
        print(f"❌ Failed to process payment receipt: {e}")
        return {"status": "error", "message": str(e)}