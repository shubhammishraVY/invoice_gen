from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from enum import Enum


class PaymentStatus(str, Enum):
    """
    Payment status enum with exactly 4 allowed values:
    - pending: Invoice created, payment not yet received
    - paid: Invoice paid before or on due date
    - due: Invoice not paid and past due date
    - due_paid: Invoice paid after due date
    """
    PENDING = "pending"
    PAID = "paid"
    DUE = "due"
    DUE_PAID = "due_paid"


class LineItem(BaseModel):
    description: str
    quantity: int
    rate: float
    amount: float


class AuthorizedSignatory(BaseModel):
    designation: str
    company: str


class InvoiceModel(BaseModel):
    usageData: Dict[str, Any]   # billingPolicy, totalBilledMinutes, totalCalls, totalSeconds
    lineItems: List[LineItem]   # NEW: Itemized breakdown of charges
    subtotal: float
    gstAmount: float
    totalAmount: float
    totalInWords: str  # NEW: Amount in words (Indian format)
    # currency: str  # NEW: Currency code (INR, USD, etc.)
    placeOfSupply: str  # NEW: GST place of supply
    # purchaseOrder: str  # NEW: PO number from client
    # poDate: Optional[str]  # NEW: PO date
    invoiceDate: str
    dueDate: str
    companyInfo: Dict[str, Any]   # includes legalName, billingEmail, bankName, accountNumber, ifscCode, billingAddress
    companyId: str
    billingRates: Dict[str, Any]  # full billing map
    billingPeriod: Dict[str, str]  # startDate, endDate
    authorizedSignatory: AuthorizedSignatory  # NEW: Signatory details
    payment_status: str