# services/razorpay_config.py
import os
from google.cloud import firestore
from services.encryption_service import EncryptionService

# Initialize Firestore
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
db = firestore.Client.from_service_account_json(SERVICE_ACCOUNT_FILE)

def get_razorpay_credentials(company_id: str) -> tuple[str, str]:
    """
    Fetch and decrypt Razorpay credentials for a specific company.
    
    Args:
        company_id: The company ID
        
    Returns:
        tuple: (razorpay_key_id, razorpay_key_secret)
    """
    try:
        print(f"🔍 Fetching Razorpay credentials for company: {company_id}")
        
        # Fetch company document
        company_ref = db.collection("companies").document(company_id)
        company_doc = company_ref.get()
        
        if not company_doc.exists:
            print(f"❌ Company {company_id} not found")
            raise ValueError(f"Company {company_id} not found")
        
        company_data = company_doc.to_dict()
        
        # ✅ FIX: Look for razorpayKeys (nested map) instead of flat fields
        razorpay_keys = company_data.get("razorpayKeys")
        
        if not razorpay_keys:
            print(f"❌ razorpayKeys not found for company {company_id}")
            raise ValueError(f"Razorpay credentials not configured for company {company_id}")
        
        # Get encrypted credentials from nested map
        encrypted_key_id = razorpay_keys.get("keyId")
        encrypted_key_secret = razorpay_keys.get("keySecret")
        
        if not encrypted_key_id or not encrypted_key_secret:
            print(f"❌ Razorpay keyId or keySecret missing for company {company_id}")
            raise ValueError(f"Razorpay credentials incomplete for company {company_id}")
        
        print(f"✅ Found Razorpay credentials")
        print(f"   Encrypted Key ID: {encrypted_key_id[:20]}...")
        print(f"   Encrypted Key Secret: {encrypted_key_secret[:20]}...")
        
        # Decrypt credentials
        # ⚠️ Note: keyId appears to be stored as plaintext, keySecret is encrypted
        key_id = encrypted_key_id  # Already plaintext in your DB
        key_secret = EncryptionService.decrypt_aes(encrypted_key_secret)
        
        if not key_secret:
            print(f"❌ Failed to decrypt Razorpay key secret for company {company_id}")
            raise ValueError("Failed to decrypt Razorpay credentials")
        
        print(f"✅ Successfully retrieved and decrypted Razorpay credentials")
        print(f"   Key ID: {key_id}")
        print(f"   Key Secret: {key_secret[:10]}...")
        
        return key_id, key_secret
        
    except Exception as e:
        print(f"❌ Error fetching Razorpay credentials: {e}")
        raise

def get_razorpay_client(company_id: str):
    """
    Create a Razorpay client for a specific company.
    
    Args:
        company_id: The company ID
        
    Returns:
        razorpay.Client: Configured Razorpay client
    """
    import razorpay
    
    key_id, key_secret = get_razorpay_credentials(company_id)
    
    print(f"🔧 Creating Razorpay client with credentials")
    return razorpay.Client(auth=(key_id, key_secret))