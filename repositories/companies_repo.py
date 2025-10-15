from db_configs.firebase_db import firestore_client

def get_company_billing_details( company_id: str, tenant_id: str | None ):
    if tenant_id is None:
        doc_ref = firestore_client.collection("companies").document(company_id)
    else:
        doc_ref = firestore_client.collection("companies").document(company_id).collection("tenants").document(tenant_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return None
    
    data = doc.to_dict()

    id = data.get("id",{})
    billing = data.get("billing", {})
    billingInfo = data.get("billingInfo",{})
    settings = data.get("settings",{})
    tzone = settings.get("timezone")
    ratePerMinute = billing.get("ratePerMinute")
    gstRate = billing.get("gstRate")
    maintenanceFee = billing.get("maintenanceFee")
    return { 
        "id": id,
        "ratePerMinute": ratePerMinute, 
        "gstRate": gstRate, 
        "maintenanceFee": maintenanceFee,
        "billing": billing,
        "billingInfo": billingInfo,
        "tzone": tzone,
    }


def get_all_companies():
    companies_ref = firestore_client.collection("companies")
    docs = companies_ref.stream()
    return [doc.id for doc in docs]


def get_tenants(company_id: str):
    tenants_ref = firestore_client.collection("companies").document(company_id).collection("tenants")
    docs = tenants_ref.stream()
    return [doc.id for doc in docs]