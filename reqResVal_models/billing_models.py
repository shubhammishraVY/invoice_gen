from pydantic import BaseModel
from typing import Optional, Dict, Any


class InvoiceModel(BaseModel):
    usageData: Dict[str, Any]   # billingPolicy, totalBilledMinutes, totalCalls, totalSeconds
    subtotal: float
    gstAmount: float
    totalAmount: float
    invoiceDate: str
    dueDate: str
    companyInfo: Dict[str, Any]   # includes legalName, billingEmail, bankName, accountNumber, ifscCode, billingAddress
    companyId: str
    billingRates: Dict[str, Any]  # full billing map
    billingPeriod: Dict[str, str] # startDate, endDate
