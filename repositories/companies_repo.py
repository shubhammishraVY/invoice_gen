from db_configs.firebase_db import firestore_client

def get_company_billing_details(company_id: str):
    doc_ref = firestore_client.collection("companies").document(company_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return None
    
    data = doc.to_dict()


    billing = data.get("billing", {})
    billingInfo = data.get("billingInfo",{})
    settings = data.get("settings",{})
    tzone = settings.get("timezone")
    ratePerMinute = billing.get("ratePerMinute")
    gstRate = billing.get("gstRate")
    maintenanceFee = billing.get("maintenanceFee")
    return { 
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
