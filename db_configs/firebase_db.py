import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    if firebase_admin._apps:
        print("✅ Firebase already initialized")
        return
    
    try:
        service_account_path = os.getenv("SERVICE_ACCOUNT_FILE")
        
        if not service_account_path:
            raise ValueError("SERVICE_ACCOUNT_FILE not set in .env file")
        
        # Check if file exists
        if not os.path.exists(service_account_path):
            raise FileNotFoundError(f"Service account file not found at: {service_account_path}")
        
        print(f"📁 Loading service account from: {service_account_path}")
        
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
        
        print("✅ Firebase Admin SDK initialized successfully")
        
    except Exception as e:
        print(f"❌ Error connecting to Firebase: {e}")
        print("   Database connection failed. Check your service account path and file integrity.")
        raise

# Initialize on import
initialize_firebase()

# Export firestore client
db = firestore.client()
firestore_client = db  # Keep backward compatibility