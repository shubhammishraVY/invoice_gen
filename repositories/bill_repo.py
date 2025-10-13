from db_configs.firebase_db import firestore_client
from datetime import datetime, timezone
from reqResVal_models.billing_models import InvoiceModel
from pydantic import ValidationError


def get_invoice(company: str, start_date: str, end_date: str):
    """
    Fetch invoice for a given company and billing period if it exists.
    """
    invoices_ref = firestore_client.collection("companies").document(company).collection("invoiceTest")
    query = (
        invoices_ref
        .where("billingPeriod.startDate", "==", start_date)
        .where("billingPeriod.endDate", "==", end_date)
        .limit(1)
    )
    results = query.stream()
    for doc in results:
        return {"id": doc.id, **doc.to_dict()}
    return None


def save_invoice(company_id: str, invoice_data: dict):
    """
    Save invoice data under companies/{company_id}/invoices.
    Validates data using Pydantic and generates a deterministic ID.
    """
    try:
        validated_invoice = InvoiceModel(**invoice_data)
        invoice_data = validated_invoice.model_dump()
    except ValidationError as e:
        raise ValueError(f"Invoice data validation failed for company {company_id}: {e}")

    invoices_ref = (
        firestore_client
        .collection("companies")
        .document(company_id)
        .collection("invoiceTest")
    )

    # 2. Deterministic ID generation from billing period
    billing_period = invoice_data.get("billingPeriod", {})
    start = billing_period.get("startDate")
    end = billing_period.get("endDate")
    
    # Fix: Convert the ISO string (e.g., '2025-09-01T...') to a datetime object
    try:
        start_date_obj = datetime.strptime(start.split('T')[0], "%Y-%m-%d")
    except (ValueError, AttributeError):
        raise ValueError("The 'startDate' format is incorrect for ID generation. Expected YYYY-MM-DDT...")

    month = start_date_obj.strftime("%m")
    year = start_date_obj.strftime("%Y")
    
    if not month or not year:
        # This check is now redundant but kept as a safeguard
        raise ValueError("The month and year not parsed correctly")

    doc_id = f"{company_id[:3].upper()}{month}{year}"
    doc_ref = invoices_ref.document(doc_id)

    # Add server timestamp
    invoice_data["createdAt"] = datetime.now(timezone.utc).isoformat()

    # Upsert → if doc exists, overwrite with latest data
    doc_ref.set(invoice_data)

    return {"id": doc_ref.id, **invoice_data}





def save_payment_record(company_id: str, payment_data: dict):
    """
    Saves a payment record under the company's 'payments' subcollection.
    Example path: companies/{company_id}/payments/{payment_id}
    """
    try:
        # Validate required data
        payment_id = payment_data.get("payment_id")
        if not payment_id:
            raise ValueError("payment_id is missing in payment_data")

        # Reference to the subcollection path
        payments_ref = (
            firestore_client
            .collection("companies")
            .document(company_id)
            .collection("payments")
        )

        # Save or update document
        payments_ref.document(payment_id).set(payment_data)

        print(f"✅ Payment record saved under {company_id}/payments/{payment_id}")

    except Exception as e:
        print(f"❌ Failed to save payment record for {company_id}: {e}")
        raise




def mark_invoice_as_paid(company_id: str, invoice_number: str, payment_data: dict):
    """
    Marks an invoice as paid and stores payment reference in the invoice document.
    """
    try:
        invoice_ref = (
            firestore_client
            .collection("companies")
            .document(company_id)
            .collection("invoiceTest")
            .document(invoice_number)
        )

        update_data = {
            "status": "Paid",
            "paymentId": payment_data.get("payment_id"),
            "paymentDate": payment_data.get("payment_date"),
            "amountPaid": payment_data.get("amount_paid"),
            "receiptPdf": payment_data.get("receipt_pdf"),
        }

        invoice_ref.update(update_data)
        print(f"✅ Invoice {invoice_number} marked as PAID for company {company_id}")

    except Exception as e:
        print(f"❌ Failed to mark invoice as paid: {e}")
        raise