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
    Save invoice data under companies/{company_id}/invoiceTest.
    Validates data using Pydantic and generates a deterministic ID.
    """
    # 1. Pydantic Data Validation
    try:
        # Validate data against the Pydantic model
        validated_invoice = InvoiceModel(**invoice_data)
        # Use the dictionary representation of the validated model for saving
        invoice_data = validated_invoice.model_dump()
    except ValidationError as e:
        # Fail early if validation check fails
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

    doc_id = f"INV_{company_id}_{month}_{year}"
    doc_ref = invoices_ref.document(doc_id)

    # Add server timestamp
    invoice_data["createdAt"] = datetime.now(timezone.utc).isoformat()

    # Upsert → if doc exists, overwrite with latest data
    doc_ref.set(invoice_data)

    return {"id": doc_ref.id, **invoice_data}