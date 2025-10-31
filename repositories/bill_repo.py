from db_configs.firebase_db import firestore_client
from datetime import datetime, timezone
from reqResVal_models.billing_models import InvoiceModel, PaymentStatus
from pydantic import ValidationError


def get_invoice(company: str, tenant: str | None, start_date: str, end_date: str):
    """
    Fetch invoice for a given company and billing period if it exists.
    """
    if tenant is None:
        invoices_ref = firestore_client.collection("companies").document(company).collection("invoices")
    else:
        invoices_ref = firestore_client.collection("companies").document(company).collection("tenants").document(tenant).collection("invoices")
    query = (
        invoices_ref
        .where("billingPeriod.startDate", "==", start_date)
        .where("billingPeriod.endDate", "==", end_date)
        .limit(1)
    )
    results = query.stream()
    for doc in results:
        return {"id": doc.id, **doc.to_dict()}
    return None


def save_invoice(company_id: str, tenant_id: str | None, invoice_data: dict):
    """
    Save invoice data under companies/{company_id}/invoices.
    Validates data using Pydantic and generates a deterministic ID.
    """
    try:
        validated_invoice = InvoiceModel(**invoice_data)
        invoice_data = validated_invoice.model_dump()
    except ValidationError as e:
        raise ValueError(f"Invoice data validation failed for company {company_id}: {e}")

    if tenant_id is None:
        invoices_ref = (firestore_client.collection("companies").document(company_id).collection("invoices"))
    else:
        invoices_ref = (firestore_client.collection("companies").document(company_id).collection("tenants").document(tenant_id).collection("invoices"))

    # 2. Deterministic ID generation from billing period
    billing_period = invoice_data.get("billingPeriod", {})
    start = billing_period.get("startDate")
    end = billing_period.get("endDate")
    
    # Fix: Convert the ISO string (e.g., '2025-09-01T...') to a datetime object
    try:
        start_date_obj = datetime.strptime(start.split('T')[0], "%Y-%m-%d")
    except (ValueError, AttributeError):
        raise ValueError("The 'startDate' format is incorrect for ID generation. Expected YYYY-MM-DDT...")

    month = start_date_obj.strftime("%m")
    year = start_date_obj.strftime("%Y")
    
    if not month or not year:
        # This check is now redundant but kept as a safeguard
        raise ValueError("The month and year not parsed correctly")
    if tenant_id is None:
        doc_id = f"{company_id[:3].upper()}{month}{year}"
    else:
        doc_id = f"{tenant_id[:3].upper()}{month}{year}"

    doc_ref = invoices_ref.document(doc_id)

    # Add server timestamp
    invoice_data["createdAt"] = datetime.now(timezone.utc).isoformat()

    # Upsert → if doc exists, overwrite with latest data
    doc_ref.set(invoice_data)

    return {"id": doc_ref.id, **invoice_data}





def save_payment_record(company_id: str, payment_data: dict, tenant_id: str | None = None):
    """
    Saves complete payment record under the company's 'payments' subcollection.
    
    Paths:
    - Top-level: companies/{company_id}/payments/REC_{invoice_number}
    - Tenant: companies/{company_id}/tenants/{tenant_id}/payments/REC_{invoice_number}
    
    Args:
        company_id: Company ID
        payment_data: Payment data dictionary
        tenant_id: Optional tenant ID for nested structure
    """
    try:
        # Validate required data
        payment_id = payment_data.get("payment_id")
        invoice_number = payment_data.get("invoice_number")
        
        if not payment_id:
            raise ValueError("payment_id is missing in payment_data")
        if not invoice_number:
            raise ValueError("invoice_number is missing in payment_data")

        # 🔧 FIX: Handle both top-level and tenant payment records
        if tenant_id is None:
            # Top-level payment record
            payments_ref = (
                firestore_client
                .collection("companies")
                .document(company_id)
                .collection("payments")
            )
            print(f"📍 Saving top-level payment: companies/{company_id}/payments/REC_{invoice_number}")
        else:
            # Tenant payment record
            payments_ref = (
                firestore_client
                .collection("companies")
                .document(company_id)
                .collection("tenants")
                .document(tenant_id)
                .collection("payments")
            )
            print(f"📍 Saving tenant payment: companies/{company_id}/tenants/{tenant_id}/payments/REC_{invoice_number}")

        # Complete payment record - NO receipt_pdf field
        payment_record = {
            "payment_id": payment_id,
            "invoice_number": invoice_number,
            "amount_paid": payment_data.get("amount_paid"),
            "currency": payment_data.get("currency"),
            "payment_date": payment_data.get("payment_date"),
            "payment_mode": payment_data.get("payment_mode"),
            "razorpay_order_id": payment_data.get("razorpay_order_id"),
            "razorpay_signature": payment_data.get("razorpay_signature"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Use REC_{invoice_number} as document ID
        doc_id = f"REC_{invoice_number}"
        payments_ref.document(doc_id).set(payment_record)

        if tenant_id is None:
            print(f"✅ Payment record saved under companies/{company_id}/payments/{doc_id}")
        else:
            print(f"✅ Payment record saved under companies/{company_id}/tenants/{tenant_id}/payments/{doc_id}")

    except Exception as e:
        print(f"❌ Failed to save payment record for {company_id}: {e}")
        raise



def mark_invoice_as_paid(company_id: str, invoice_number: str, payment_data: dict, tenant_id: str | None = None):
    """
    Marks an invoice as paid - updates payment_status based on due date.
    - If paid before or on due date: status = "paid"
    - If paid after due date: status = "due_paid"
    
    Paths:
    - Top-level: companies/{company_id}/invoices/{invoice_number}
    - Tenant: companies/{company_id}/tenants/{tenant_id}/invoices/{invoice_number}
    
    Args:
        company_id: Company ID
        invoice_number: Invoice ID/number
        payment_data: Payment data (currently unused but kept for backwards compatibility)
        tenant_id: Optional tenant ID for nested invoices
    """
    try:
        # 🔧 FIX: Handle both top-level and nested tenant invoices
        if tenant_id is None:
            invoice_ref = (
                firestore_client
                .collection("companies")
                .document(company_id)
                .collection("invoices")
                .document(invoice_number)
            )
            print(f"📍 Updating top-level invoice: companies/{company_id}/invoices/{invoice_number}")
        else:
            invoice_ref = (
                firestore_client
                .collection("companies")
                .document(company_id)
                .collection("tenants")
                .document(tenant_id)
                .collection("invoices")
                .document(invoice_number)
            )
            print(f"📍 Updating tenant invoice: companies/{company_id}/tenants/{tenant_id}/invoices/{invoice_number}")

        # Fetch the invoice to get the due date
        invoice_doc = invoice_ref.get()
        if not invoice_doc.exists:
            raise ValueError(f"Invoice {invoice_number} not found at the expected path")
        
        invoice_data = invoice_doc.to_dict()
        due_date_str = invoice_data.get("dueDate")
        
        if not due_date_str:
            raise ValueError(f"Invoice {invoice_number} has no due date")
        
        # Parse due date (ISO format string)
        try:
            due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            # Try parsing just the date part
            due_date = datetime.strptime(due_date_str.split('T')[0], "%Y-%m-%d")
            due_date = due_date.replace(tzinfo=timezone.utc)
        
        # Get current date
        current_date = datetime.now(timezone.utc)
        
        # Determine payment status based on due date
        if current_date.date() <= due_date.date():
            payment_status = PaymentStatus.PAID.value
            status_msg = "paid (on time)"
        else:
            payment_status = PaymentStatus.DUE_PAID.value
            status_msg = "due_paid (paid after due date)"

        # Update only payment_status
        update_data = {
            "payment_status": payment_status,
        }

        invoice_ref.update(update_data)
        print(f"✅ Invoice {invoice_number} payment_status updated to '{status_msg}'")

    except Exception as e:
        print(f"❌ Failed to mark invoice as paid: {e}")
        raise


def update_overdue_invoices(company_id: str, tenant_id: str | None = None):
    """
    Updates all pending invoices past their due date to 'due' status.
    Can be called periodically or on-demand.
    
    Args:
        company_id: The company ID
        tenant_id: Optional tenant ID for nested structure
        
    Returns:
        dict: Summary of updates performed
    """
    try:
        # Get reference to invoices collection
        if tenant_id is None:
            invoices_ref = (
                firestore_client
                .collection("companies")
                .document(company_id)
                .collection("invoices")
            )
        else:
            invoices_ref = (
                firestore_client
                .collection("companies")
                .document(company_id)
                .collection("tenants")
                .document(tenant_id)
                .collection("invoices")
            )
        
        # Query for pending invoices
        pending_invoices = (
            invoices_ref
            .where("payment_status", "==", PaymentStatus.PENDING.value)
            .stream()
        )
        
        current_date = datetime.now(timezone.utc)
        updated_count = 0
        skipped_count = 0
        
        for invoice_doc in pending_invoices:
            invoice_data = invoice_doc.to_dict()
            invoice_id = invoice_doc.id
            due_date_str = invoice_data.get("dueDate")
            
            if not due_date_str:
                print(f"⚠️ Invoice {invoice_id} has no due date, skipping")
                skipped_count += 1
                continue
            
            # Parse due date
            try:
                due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                try:
                    due_date = datetime.strptime(due_date_str.split('T')[0], "%Y-%m-%d")
                    due_date = due_date.replace(tzinfo=timezone.utc)
                except Exception:
                    print(f"⚠️ Invoice {invoice_id} has invalid due date format, skipping")
                    skipped_count += 1
                    continue
            
            # Check if past due
            if current_date.date() > due_date.date():
                # Update to 'due' status
                invoice_doc.reference.update({
                    "payment_status": PaymentStatus.DUE.value
                })
                print(f"✅ Invoice {invoice_id} updated from 'pending' to 'due'")
                updated_count += 1
        
        summary = {
            "updated": updated_count,
            "skipped": skipped_count,
            "message": f"Updated {updated_count} overdue invoices to 'due' status"
        }
        print(f"📊 {summary['message']}")
        return summary
        
    except Exception as e:
        print(f"❌ Failed to update overdue invoices: {e}")
        raise


def update_all_overdue_invoices():
    """
    Updates overdue invoices across all companies.
    This function can be called by a scheduled task or endpoint.
    
    Returns:
        dict: Summary of all updates
    """
    try:
        total_updated = 0
        total_skipped = 0
        companies_processed = 0
        
        # Get all companies
        companies_ref = firestore_client.collection("companies")
        companies = companies_ref.stream()
        
        for company_doc in companies:
            company_id = company_doc.id
            print(f"🔍 Processing company: {company_id}")
            
            # Update top-level invoices
            try:
                result = update_overdue_invoices(company_id, tenant_id=None)
                total_updated += result["updated"]
                total_skipped += result["skipped"]
            except Exception as e:
                print(f"⚠️ Error processing company {company_id}: {e}")
            
            # Check for tenants
            tenants_ref = company_doc.reference.collection("tenants")
            tenants = tenants_ref.stream()
            
            for tenant_doc in tenants:
                tenant_id = tenant_doc.id
                print(f"🔍 Processing tenant: {company_id}/{tenant_id}")
                try:
                    result = update_overdue_invoices(company_id, tenant_id)
                    total_updated += result["updated"]
                    total_skipped += result["skipped"]
                except Exception as e:
                    print(f"⚠️ Error processing tenant {company_id}/{tenant_id}: {e}")
            
            companies_processed += 1
        
        summary = {
            "companies_processed": companies_processed,
            "total_updated": total_updated,
            "total_skipped": total_skipped,
            "message": f"Processed {companies_processed} companies, updated {total_updated} overdue invoices"
        }
        print(f"✅ {summary['message']}")
        return summary
        
    except Exception as e:
        print(f"❌ Failed to update all overdue invoices: {e}")
        raise


def get_all_pending_invoices():
    """
    Fetches all invoices with payment_status='pending' across all companies and tenants.
    
    Returns:
        list: List of dictionaries containing invoice data with metadata
              Each dict contains: invoice_data, company_id, tenant_id (or None)
    """
    try:
        pending_invoices = []
        
        # Get all companies
        companies_ref = firestore_client.collection("companies")
        companies = companies_ref.stream()
        
        for company_doc in companies:
            company_id = company_doc.id
            
            # Query top-level invoices for this company
            try:
                invoices_ref = company_doc.reference.collection("invoices")
                pending_query = invoices_ref.where("payment_status", "==", PaymentStatus.PENDING.value)
                
                for invoice_doc in pending_query.stream():
                    invoice_data = invoice_doc.to_dict()
                    invoice_data["invoice_id"] = invoice_doc.id
                    pending_invoices.append({
                        "invoice_data": invoice_data,
                        "company_id": company_id,
                        "tenant_id": None
                    })
            except Exception as e:
                print(f"⚠️ Error fetching invoices for company {company_id}: {e}")
            
            # Query tenant invoices
            tenants_ref = company_doc.reference.collection("tenants")
            tenants = tenants_ref.stream()
            
            for tenant_doc in tenants:
                tenant_id = tenant_doc.id
                try:
                    tenant_invoices_ref = tenant_doc.reference.collection("invoices")
                    tenant_pending_query = tenant_invoices_ref.where("payment_status", "==", PaymentStatus.PENDING.value)
                    
                    for invoice_doc in tenant_pending_query.stream():
                        invoice_data = invoice_doc.to_dict()
                        invoice_data["invoice_id"] = invoice_doc.id
                        pending_invoices.append({
                            "invoice_data": invoice_data,
                            "company_id": company_id,
                            "tenant_id": tenant_id
                        })
                except Exception as e:
                    print(f"⚠️ Error fetching invoices for tenant {company_id}/{tenant_id}: {e}")
        
        print(f"📋 Found {len(pending_invoices)} pending invoices")
        return pending_invoices
        
    except Exception as e:
        print(f"❌ Failed to fetch pending invoices: {e}")
        raise