from db_configs.firebase_db import firestore_client

def get_invoice_by_id(company_id: str, tenant_id: str | None, invoice_id: str):
    try:
        if tenant_id is None:
            doc_ref = firestore_client.collection("companies").document(company_id).collection("invoices").document(invoice_id)
        else:
            doc_ref = firestore_client.collection("companies").document(company_id).collection("tenants").document(tenant_id).collection("invoices").document(invoice_id)
        doc = doc_ref.get()
        if not doc.exists:
            return None
        return doc.to_dict()
    except Exception as e:
        print(f"Error fetching invoice: {e}")
        return None