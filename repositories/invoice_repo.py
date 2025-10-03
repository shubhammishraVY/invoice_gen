from db_configs.firebase_db import firestore_client
from datetime import datetime, timezone


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
    Uses deterministic ID based on billing period.
    """
    invoices_ref = (
        firestore_client
        .collection("companies")
        .document(company_id)
        .collection("invoiceTest")
    )

    # Deterministic ID from billing period
    billing_period = invoice_data.get("billingPeriod", {})
    start = billing_period.get("startDate")
    end = billing_period.get("endDate")

    if not start or not end:
        raise ValueError("Invoice must include billingPeriod.startDate and billingPeriod.endDate")

    doc_id = f"{start}_{end}"  # unique per cycle
    doc_ref = invoices_ref.document(doc_id)

    # Add server timestamp
    invoice_data["createdAt"] = datetime.now(timezone.utc).isoformat()

    # Upsert → if doc exists, overwrite with latest data
    doc_ref.set(invoice_data)

    return {"id": doc_ref.id, **invoice_data}
