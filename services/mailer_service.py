import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# --- Configuration (REPLACE THESE VALUES) ---
# IMPORTANT: For security, never use your regular password. Use an 'App Password'
# generated from your email provider (e.g., Google, Microsoft).
SMTP_SERVER = "smtp.gmail.com"  # Example for Gmail
SMTP_PORT = 587                  # Standard port for TLS encryption
SENDER_EMAIL = "shubham.mishra@vysedeck.com"
SENDER_PASSWORD = "evzp clsy edcu tsfa" # Use App Password, NOT main password
# ---------------------------------------------

def send_invoice_email(recipient_email: str, company_name: str, invoice_number: str, pdf_path: str, invoice_data: dict):
    """
    Sends an invoice email with the PDF attached and detailed billing information.
    
    Args:
        recipient_email (str): The client's email address.
        company_name (str): The client's company legal name.
        invoice_number (str): The unique invoice ID.
        pdf_path (str): The local path to the generated PDF file.
        invoice_data (dict): The complete invoice data including usage stats and amounts.
    """
    try:
        # Extract billing details from invoice_data
        usage_data = invoice_data.get('usageData', {})
        total_calls = usage_data.get('totalCalls', 0)
        total_billed_minutes = usage_data.get('totalBilledMinutes', 0)
        
        billing_rates = invoice_data.get('billingRates', {})
        rate_per_minute = billing_rates.get('ratePerMinute', 0)
        maintenance_fee = billing_rates.get('maintenanceFee', 0)
        gst_rate = billing_rates.get('gstRate', 0)
        currency = invoice_data.get('currency', 'INR')
        
        subtotal = invoice_data.get('subtotal', 0)
        gst_amount = invoice_data.get('gstAmount', 0)
        total_amount = invoice_data.get('totalAmount', 0)
        
        billing_period = invoice_data.get('billingPeriod', {})
        start_date = billing_period.get('startDate', '')[:10]  # YYYY-MM-DD
        end_date = billing_period.get('endDate', '')[:10]
        
        due_date = invoice_data.get('dueDate', '')[:10]
        
        # Calculate call charges (subtotal minus maintenance fee)
        call_charges = subtotal - maintenance_fee
        
        # Currency symbol
        currency_symbol = "₹" if currency == "INR" else currency
        
        # Create a multipart message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = f"Tax Invoice {invoice_number} - Voice Agent Services for {start_date} to {end_date}"

        # Email body (HTML for better formatting)
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <p>Dear Sir/Madam,</p>
                
                <p>Greetings from <strong>VYSEDECK AI Ventures Pvt Ltd</strong>!</p>
                
                <p>Please find attached the tax invoice <strong>{invoice_number}</strong> for Voice Agent services consumed during the billing period <strong>{start_date} to {end_date}</strong>.</p>
                
                <div style="background-color: #f5f7fa; padding: 20px; border-left: 4px solid #104084; margin: 20px 0;">
                    <h3 style="color: #104084; margin-top: 0;">Invoice Summary</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0;"><strong>1. Total Calls:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{total_calls:,}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>2. Total Billed Minutes:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{total_billed_minutes:,} minutes</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>3. Call Charges (@ {currency_symbol}{rate_per_minute}/min):</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{currency_symbol} {call_charges:,.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>4. Maintenance Charge:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{currency_symbol} {maintenance_fee:,.2f}</td>
                        </tr>
                        <tr style="border-top: 1px solid #ddd;">
                            <td style="padding: 8px 0;"><strong>Subtotal:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{currency_symbol} {subtotal:,.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>5. GST ({gst_rate}%):</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{currency_symbol} {gst_amount:,.2f}</td>
                        </tr>
                        <tr style="border-top: 2px solid #104084; background-color: #e8f0f8;">
                            <td style="padding: 12px 0; font-size: 16px;"><strong>6. Total Payable Amount:</strong></td>
                            <td style="padding: 12px 0; text-align: right; font-size: 16px; color: #104084;"><strong>{currency_symbol} {total_amount:,.2f}</strong></td>
                        </tr>
                    </table>
                </div>
                
                <p><strong>Payment Due Date:</strong> {due_date}</p>
                
                <p>The attached PDF contains complete invoice details including payment instructions and bank account information. Please refer to the document for full terms and conditions.</p>
                
                <p>Kindly process the payment by the due date mentioned above. For any queries or clarifications regarding this invoice, please feel free to contact us.</p>
                
                <br>
                <p>Thank you for your continued business.</p>
                
                <p>Best regards,<br>
                <strong>VYSEDECK Billing Team</strong><br>
                VYSEDECK AI Ventures Pvt Ltd<br>
                Email: {SENDER_EMAIL}<br>
                Phone: +91 9999999999</p>
                
                <hr style="border: 0; border-top: 1px solid #eee; margin-top: 30px;">
                <p style="font-size: 11px; color: #777;">
                    <em>This is an automated email. Please do not reply directly to this address. For support, contact us at the details provided above.</em>
                </p>
            </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))

        # Attach the PDF file
        with open(pdf_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        # Encode file in base64
        encoders.encode_base64(part)

        # Add header as key/value pair to attachment part
        filename = os.path.basename(pdf_path)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {filename}",
        )

        # Attach the body and the PDF file to the message
        msg.attach(part)
        
        # Connect to the SMTP server and send the email
        print(f"Attempting to connect to SMTP server at {SMTP_SERVER}:{SMTP_PORT}...")
        
        # Use a context manager to ensure the connection is closed
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()  # Can be omitted
            server.starttls()  # Upgrade connection to secure mode (TLS)
            server.ehlo()  # Can be omitted
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        
        print(f"Email sent successfully to {recipient_email}")

    except smtplib.SMTPAuthenticationError:
        print(f"AUTHENTICATION FAILED. Please check SENDER_EMAIL and SENDER_PASSWORD (ensure it's an App Password).")
        raise
    except smtplib.SMTPException as e:
        print(f"SMTP Error occurred: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred while sending email: {e}")
        raise