from fastapi import Request, HTTPException
from firebase_admin import auth
import firebase_admin

def verify_firebase_token( request: Request ):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    id_token = auth_header.split(" ")[1]

    try:
        decoded_token = auth.verify_id_token(id_token)
        request.state.user = decoded_token
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Token: {str(e)}")