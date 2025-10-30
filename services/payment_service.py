import stripe
import razorpay
import os
import hmac
import hashlib
from dotenv import load_dotenv
from datetime import datetime
from services.pdf_service import generate_pdf
from services.mailer_service import send_email
from repositories.bill_repo import save_payment_record, mark_invoice_as_paid
load_dotenv()

#--- Stripe Setup ---
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

#--- Razorpay Setup ---
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

razorpay_client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
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


# ================== NEW FUNCTION: VERIFY RAZORPAY SIGNATURE ==================
def verify_razorpay_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    """
    Verifies Razorpay payment signature to ensure payment authenticity.
    
    Args:
        razorpay_order_id: Order ID from Razorpay
        razorpay_payment_id: Payment ID from Razorpay
        razorpay_signature: Signature from Razorpay
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    try:
        # Construct the message
        message = f"{razorpay_order_id}|{razorpay_payment_id}"
        
        # Generate expected signature using HMAC SHA256
        expected_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        is_valid = hmac.compare_digest(expected_signature, razorpay_signature)
        
        if is_valid:
            print(f"✅ Razorpay signature verified successfully")
        else:
            print(f"❌ Razorpay signature verification failed")
            print(f"   Expected: {expected_signature}")
            print(f"   Received: {razorpay_signature}")
        
        return is_valid
        
    except Exception as e:
        print(f"❌ Error verifying Razorpay signature: {e}")
        return False


# ================== NEW FUNCTION: VERIFY AND PROCESS PAYMENT ==================
def verify_razorpay_payment(
    razorpay_payment_id: str,
    razorpay_order_id: str,
    razorpay_signature: str,
    invoice_data: dict,
    company_id: str,
    tenant_id: str | None,
    invoice_id: str
) -> dict:
    """
    Verifies Razorpay payment signature and processes the payment.
    This is the main function called after a successful Razorpay payment.
    
    Args:
        razorpay_payment_id: Payment ID from Razorpay
        razorpay_order_id: Order ID from Razorpay
        razorpay_signature: Signature from Razorpay
        invoice_data: Invoice data from Firestore
        company_id: Company ID
        tenant_id: Tenant ID (optional)
        invoice_id: Invoice ID
        
    Returns:
        dict: Result of payment processing
    """
    print("=" * 50)
    print("🔐 VERIFYING RAZORPAY PAYMENT")
    print(f"Payment ID: {razorpay_payment_id}")
    print(f"Order ID: {razorpay_order_id}")
    
    try:
        # 1️⃣ Verify signature
        is_valid = verify_razorpay_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature)
        
        if not is_valid:
            print("❌ Invalid Razorpay signature - Payment verification failed!")
            return {
                "status": "error",
                "message": "Invalid payment signature. Payment verification failed."
            }
        
        print("✅ Signature verified - Payment is authentic")
        
        # 2️⃣ Prepare payment data for receipt generation
        payment_info = {
            **invoice_data,  # Include all invoice data
            "invoice_number": invoice_id,
            "companyId": company_id,
            "tenant_id": tenant_id,
            "payment_id": razorpay_payment_id,
            "order_id": razorpay_order_id,
            "razorpay_signature": razorpay_signature,
            "payment_date": datetime.utcnow().isoformat(),
            "payment_mode": "Razorpay",
        }
        
        print("📧 Generating and sending payment receipt...")
        
        # 3️⃣ Generate receipt, email it, and update database
        result = generate_payment_receipt(payment_info)
        
        if result.get("status") == "success":
            print("✅ Payment processed successfully!")
            print("=" * 50)
            return {
                "status": "success",
                "message": "Payment verified and processed successfully",
                "invoice_id": invoice_id,
                "payment_id": razorpay_payment_id,
                "receipt_pdf": result.get("receipt_pdf")
            }
        else:
            print(f"⚠️ Receipt generation failed: {result.get('message')}")
            return {
                "status": "error",
                "message": f"Payment verified but receipt generation failed: {result.get('message')}"
            }
            
    except Exception as e:
        print(f"❌ Error processing payment: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Payment processing failed: {str(e)}"
        }


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

        print(f"📄 Generating receipt for invoice {invoice_number}")
        print(f"   Company: {company_name}")
        print(f"   Amount: {total_amount} {currency}")
        print(f"   Payment ID: {payment_id}")

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
        print(f"✅ PDF generated: {pdf_path}")

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
            "payment_url": f"{os.getenv('FRONTEND_URL', 'https://billai.vysedeck.com')}/payments",
        }

        send_email(
            # recipient_email=recipient_email,
            recipient_email="vishruth.ramesh@vysedeck.com",  # for testing purposes
            subject=subject,
            html_template="receipt_email_template.html",
            context=context,
            attachments=[pdf_path],
        )

        print(f"✅ Payment receipt emailed successfully to vishruth.ramesh@vysedeck.com")

        # --- 3️⃣ Save COMPLETE Payment Record in payments collection ---
        save_payment_record(companyId, {
            "payment_id": payment_id,
            "invoice_number": invoice_number,
            "amount_paid": total_amount,
            "currency": currency,
            "payment_date": payment_date,
            "payment_mode": payment_mode,
            "razorpay_order_id": payment_data.get("order_id"),
            "razorpay_signature": payment_data.get("razorpay_signature"),
        })
        print(f"✅ Payment record saved in Firestore")

        # --- 4️⃣ Update ONLY payment_status in invoice ---
        mark_invoice_as_paid(companyId, invoice_number, {})
        print(f"✅ Invoice {invoice_number} marked as paid")

        return {"status": "success", "receipt_pdf": pdf_path}

    except Exception as e:
        print(f"❌ Failed to process payment receipt: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}