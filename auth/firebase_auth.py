# auth/firebase_auth.py
from fastapi import HTTPException, Header
from firebase_admin import auth
import firebase_admin

def verify_firebase_token(authorization: str = Header(None)):
    """
    Verify Firebase ID token from Authorization header.
    
    Args:
        authorization: Authorization header in format "Bearer <token>"
        
    Returns:
        dict: Decoded token containing user information
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    print(f"🔐 Authorization header received: {authorization[:50] if authorization else 'None'}...")
    
    if not authorization:
        print("❌ No Authorization header provided")
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )
    
    if not authorization.startswith("Bearer "):
        print("❌ Invalid Authorization header format")
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'"
        )
    
    token = authorization.split("Bearer ")[1].strip()
    
    if not token:
        print("❌ Empty token in Authorization header")
        raise HTTPException(
            status_code=401,
            detail="Empty token"
        )
    
    try:
        print(f"🔐 Verifying Firebase token: {token[:20]}...")
        
        # Verify the token with Firebase Admin SDK
        decoded_token = auth.verify_id_token(token)
        
        print(f"✅ Token verified successfully")
        print(f"   User ID: {decoded_token.get('uid')}")
        print(f"   Email: {decoded_token.get('email')}")
        
        return decoded_token
        
    except auth.InvalidIdTokenError as e:
        print(f"❌ Invalid Firebase token: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid Firebase token: {str(e)}"
        )
    except auth.ExpiredIdTokenError as e:
        print(f"❌ Expired Firebase token: {e}")
        raise HTTPException(
            status_code=401,
            detail="Firebase token has expired. Please log in again."
        )
    except auth.RevokedIdTokenError as e:
        print(f"❌ Revoked Firebase token: {e}")
        raise HTTPException(
            status_code=401,
            detail="Firebase token has been revoked"
        )
    except auth.CertificateFetchError as e:
        print(f"❌ Error fetching Firebase certificates: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error verifying token. Please try again later."
        )
    except ValueError as e:
        print(f"❌ Value error in token verification: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token format: {str(e)}"
        )
    except Exception as e:
        print(f"❌ Unexpected error verifying token: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=401,
            detail=f"Token verification failed: {str(e)}"
        )