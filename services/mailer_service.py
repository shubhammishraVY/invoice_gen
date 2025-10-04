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

def send_invoice_email(recipient_email: str, company_name: str, invoice_number: str, pdf_path: str):
    """
    Sends an invoice email with the PDF attached.
    
    Args:
        recipient_email (str): The client's email address.
        company_name (str): The client's company legal name.
        invoice_number (str): The unique invoice ID.
        pdf_path (str): The local path to the generated PDF file.
    """
    try:
        # Create a multipart message
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = f"VYSEDECK AI: Invoice {invoice_number} for {company_name}"

        # Email body (HTML is recommended for better formatting)
        body = f"""
        <html>
            <body>
                <p>Dear {company_name} team,</p>
                <p>Please find attached your monthly tax invoice, {invoice_number}, for the services rendered by VYSEDECK AI Ventures Pvt Ltd.</p>
                <p>The invoice is due on the date specified in the document. Please refer to the PDF for payment instructions and details.</p>
                <br>
                <p>Thank you for your timely payment.</p>
                <br>
                <p>Best regards,</p>
                <p>The VYSEDECK Billing Team</p>
                <hr style="border: 0; border-top: 1px solid #eee;">
                <p style="font-size: 10px; color: #777;">This is an automated email. Please do not reply to this address.</p>
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
        print(f"📧 Attempting to connect to SMTP server at {SMTP_SERVER}:{SMTP_PORT}...")
        
        # Use a context manager to ensure the connection is closed
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()  # Can be omitted
            server.starttls()  # Upgrade connection to secure mode (TLS)
            server.ehlo()  # Can be omitted
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        
        print(f"✅ Email sent successfully to {recipient_email}")

    except smtplib.SMTPAuthenticationError:
        print(f"AUTHENTICATION FAILED. Please check SENDER_EMAIL and SENDER_PASSWORD (ensure it's an App Password).")
        raise
    except smtplib.SMTPException as e:
        print(f"SMTP Error occurred: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred while sending email: {e}")
        raise

