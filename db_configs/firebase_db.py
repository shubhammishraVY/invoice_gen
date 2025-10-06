import firebase_admin
from firebase_admin import credentials, firestore
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

try:

    # SERVICE_ACCOUNT_FILE = Path(__file__).parent / "vysedeck-voiceagent-firebase-adminsdk-fbsvc-99ac27dfda.json"
    # print (SERVICE_ACCOUNT_FILE)

    # cred_path = os.environ.get("FIREBASE_CRED_PATH", "D:\Documents\VYSEDECK\Projects\Billing_For_calls\db_configs\vysedeck-voiceagent-firebase-adminsdk-fbsvc-99ac27dfda.json")
   
    if not firebase_admin._apps:
        cred = credentials.Certificate(os.getenv("SERVICE_ACCOUNT_FILE"))
        firebase_admin.initialize_app(cred)

    # Get Firestore client
    firestore_client = firestore.client()

    print("Connected to Firestore!")

except Exception as e:
    print(f"Error connecting to Firebase:{e}")

    db = None
    print("database connection failed. Check your service account path and file integrity.")