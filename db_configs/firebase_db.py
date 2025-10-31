import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv()

try:
    # Get credentials path from environment variable
    SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not SERVICE_ACCOUNT_FILE:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not set in .env file")

    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"Firebase credentials file not found at: {SERVICE_ACCOUNT_FILE}")

    # Initialize Firebase Admin if not already initialized
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
        firebase_admin.initialize_app(cred)

    # Get Firestore client
    firestore_client = firestore.client()
    print("✅ Connected to Firestore successfully!")

except Exception as e:
    print(f"❌ Error connecting to Firebase: {e}")
    firestore_client = None
    print("   Database connection failed. Check your service account path and file integrity.")