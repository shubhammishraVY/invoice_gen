import jwt
from datetime import datetime, timedelta

SECRET_KEY = "super-secret"  # move to env var in prod

def generate_invoice_token(company_id: str, tenant_id: str | None, invoice_id: str, expires_in_hours=72):
    """
    Generates a signed JWT token for a single invoice.
    """
    payload = {
        "company_id": company_id,
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "exp": datetime.utcnow() + timedelta(hours=expires_in_hours),
        "used": False  # optional single-use flag
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def verify_invoice_token(token: str):
    """
    Verifies the token, checks expiration and returns payload.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if payload.get("used"):
            raise Exception("Token already used")
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Token expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")
