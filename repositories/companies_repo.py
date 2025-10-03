from db_configs.firebase_db import firestore_client

def get_company_billing_details(company_id: str):
    doc_ref = firestore_client.collection("companies").document(company_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return None
    
    data = doc.to_dict()


    billing = data.get("billing", {})
    billingInfo = data.get("billingInfo",{})

    ratePerMinute = billing.get("ratePerMinute")
    gstRate = billing.get("gstRate")
    maintenanceFee = billing.get("maintenanceFee")
    return { 
        "ratePerMinute": ratePerMinute, 
        "gstRate": gstRate, 
        "maintenanceFee": maintenanceFee,
        "billing": billing,
        "billingInfo": billingInfo
    }